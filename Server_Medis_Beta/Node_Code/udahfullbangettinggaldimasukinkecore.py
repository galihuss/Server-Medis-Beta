import time
import os
import glob
import RPi.GPIO as GPIO
from pymodbus.client import ModbusSerialClient

# ==== SETUP GPIO ====
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# === HX711 Load Cell Pins ===
DT = 5
SCK = 6
GPIO.setup(SCK, GPIO.OUT)
GPIO.setup(DT, GPIO.IN)

# === Ultrasonic Sensor Pins ===
TRIG = 23
ECHO = 24
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# ==== GLOBAL MODBUS DATA ====
modbus_values = {
    "alkohol": None,
    "warna": None,
}

last_color_code = None

# === SETUP MODBUS CLIENT ===
def setup_modbus():
    try:
        client = ModbusSerialClient(
            method='rtu',
            port='/dev/ttyUSB0',  # sesuaikan port
            baudrate=9600,
            stopbits=1,
            bytesize=8,
            parity='N',
            timeout=3
        )
        if not client.connect():
            print("Modbus connection failed")
            return None
        print("Modbus connected successfully")
        return client
    except Exception as e:
        print(f"Modbus init error: {str(e)}")
        return None

# === BACA SENSOR MODBUS ===
def read_modbus_sensors(client):
    if not client:
        return None, None
    try:
        # Baca 2 register dari alamat 0, slave ID 1
        result = client.read_holding_registers(address=0, count=2, unit=1)
        
        if result.isError():
            print(f"Modbus read error: {result}")
            return None, None
        
        if not hasattr(result, 'registers') or len(result.registers) < 2:
            print("Modbus returned incomplete data")
            print(f"Registers received: {getattr(result, 'registers', None)}")
            return None, None
        
        alkohol_raw = result.registers[0]
        warna_code = result.registers[1]

        # Konversi sensor alkohol dari nilai ADC ke voltase
        alkohol = alkohol_raw * (5.0 / 1023.0)
        return alkohol, warna_code

    except Exception as e:
        print(f"Modbus read exception: {str(e)}")
        return None, None

# === HX711 FUNCTIONS ===
def read_hx711():
    GPIO.output(SCK, 0)
    while GPIO.input(DT) == 1:
        time.sleep(0.001)
    count = 0
    for _ in range(24):
        GPIO.output(SCK, 1)
        count = count << 1
        if GPIO.input(DT):
            count += 1
        GPIO.output(SCK, 0)
    GPIO.output(SCK, 1)
    GPIO.output(SCK, 0)
    if count & 0x800000:
        count -= 0x1000000
    return count

def average_read(times=10):
    readings = []
    for _ in range(times):
        reading = read_hx711()
        readings.append(reading)
        time.sleep(0.05)
    return sum(readings) / len(readings)

# --- DS18B20 Temperature Sensor ---
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
base_dir = '/sys/bus/w1/devices/'
try:
    device_path = glob.glob(base_dir + '28*')[0]
    rom = device_path.split('/')[-1]
except IndexError:
    print("Error: Temperature sensor not found!")
    exit()

def read_temp_raw():
    try:
        with open(device_path + '/w1_slave', 'r') as f:
            return f.readlines()
    except Exception as e:
        print(f"Temp read error: {str(e)}")
        return ["", "t=0"]

def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_c = float(lines[1][equals_pos+2:]) / 1000.0
        return temp_c
    return 0.0

# ==== SENSOR ULTRASONIC READING ====
def read_ultrasonic(max_attempts=3):
    for attempt in range(max_attempts):
        try:
            GPIO.output(TRIG, False)
            time.sleep(0.05)

            GPIO.output(TRIG, True)
            time.sleep(0.00001)
            GPIO.output(TRIG, False)

            timeout = time.time() + 0.1
            pulse_start = pulse_end = time.time()

            while GPIO.input(ECHO) == 1 and time.time() < timeout:
                pass
            while GPIO.input(ECHO) == 0 and time.time() < timeout:
                pulse_start = time.time()
            while GPIO.input(ECHO) == 1 and time.time() < timeout:
                pulse_end = time.time()

            if pulse_start >= pulse_end:
                raise ValueError("Invalid pulse reading")

            distance = (pulse_end - pulse_start) * 17150
            return round(distance, 2)

        except Exception as e:
            print(f"Ultrasonic attempt {attempt+1} failed: {str(e)}")
            time.sleep(0.1)
    return -1

# ==== MAIN PROGRAM ====
def main():
    print("\n=== SMART SYSTEM WITH SENSOR FUSION ===")
    modbus_client = setup_modbus()

    faktor_kalibrasi = -102.23  # bit per gram (load cell calibration)
    offset_manual = 104         # offset gram

    if modbus_client:
        print("Starting sensor loop...")

    global last_color_code

    try:
        while True:
            # Baca sensor ultrasonik dan load cell setiap loop
            suhu = read_temp()
            jarak = read_ultrasonic()
            nilai_load = average_read()
            berat = (nilai_load) / faktor_kalibrasi - offset_manual

            # Baca sensor modbus (alkohol dan warna)
            alkohol, warna = read_modbus_sensors(modbus_client)

            if alkohol is not None and warna is not None:
                # Update hanya jika kode warna berubah (mewakili pembacaan baru warna)
                if warna != last_color_code:
                    modbus_values["alkohol"] = alkohol
                    modbus_values["warna"] = warna
                    last_color_code = warna
                    print(f"[New Data] Alkohol Voltage: {alkohol:.3f} V, Color Code: {warna}")

            # Tampilkan semua data tiap loop
            print("\n" + "="*40)
            print(f"[{time.strftime('%H:%M:%S')}]")
            print(f"Distance     : {jarak if jarak != -1 else 'ERROR'} cm")
            print(f"Temperature: {suhu:.2f}°C")
            if modbus_values["alkohol"] is not None:
                print(f"Alcohol      : {modbus_values['alkohol']:.3f} V")
                print(f"Color Code   : {modbus_values['warna']}")
            else:
                print("Modbus data  : Not available yet")

            print(f"Weight       : {berat:.2f} gram")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down system...")

    finally:
        GPIO.cleanup()
        if modbus_client:
            modbus_client.close()

if __name__ == "__main__":
    main()

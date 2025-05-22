import os
import glob
import time
import RPi.GPIO as GPIO
from pymodbus.client import ModbusSerialClient
import json

# ==== SETUP GPIO ====
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# === HX711 Load Cell Pins ===
DT = 5
SCK = 6
GPIO.setup(SCK, GPIO.OUT)
GPIO.setup(DT, GPIO.IN)

# --- Ultrasonic Sensor ---
TRIG = 23
ECHO = 24
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def read_ultrasonik(max_attempts=3):
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

# --- Modbus RTU Client ---
def setup_modbus():
    try:
        client = ModbusSerialClient(
            method='rtu',
            port='/dev/ttyUSB0',
            baudrate=9600,
            stopbits=1,
            bytesize=8,
            parity='N',
            timeout=1
        )
        if not client.connect():
            print("Modbus connection failed")
            return None
        print("Modbus connected successfully")
        return client
    except Exception as e:
        print(f"Modbus init error: {str(e)}")
        return None

def read_modbus_sensors(client):
    if not client:
        return None, None
    try:
        result = client.read_holding_registers(address=0, count=2, slave=1)
        if result.isError():
            print("Modbus read error:", result)
            return None, None
        alkohol = result.registers[0] * (5.0 / 1023.0)
        foto = result.registers[1] * (5.0 / 1023.0)
        return alkohol, foto
    except Exception as e:
        print(f"Modbus read exception: {str(e)}")
        return None, None

# === HX711 Functions ===
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

# === MAIN PROGRAM ===
def main():
    print("\n=== SMART SYSTEM WITH SENSOR FUSION ===")
    modbus_client = setup_modbus()

    # Nilai kalibrasi dari hasil regresi
    faktor_kalibrasi = -102.23  # bit per gram
    offset_manual = 104  # Nilai offset manual

    try:
        while True:
            # Baca semua sensor
            suhu = read_temp()
            jarak = read_ultrasonik()
            alkohol, foto = read_modbus_sensors(modbus_client)
            nilai_load = average_read()

            # Hitung berat dengan formula yang diberikan
            berat = (nilai_load) / faktor_kalibrasi - offset_manual

            # Buat data dalam format JSON
            data = {
                "temperature": suhu,
                "alcohol": alkohol,
                "urine": foto,
                "berat": berat,
                "tinggi": jarak
            }

            # Tampilkan hasil pembacaan dalam format JSON
            print("\n" + "="*40)
            print(f"[{time.strftime('%H:%M:%S')}] Data JSON:")
            print(json.dumps(data, indent=4))

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down system...")
    finally:
        GPIO.cleanup()
        if modbus_client:
            modbus_client.close()
        print("System safely terminated")

if __name__ == "__main__":
    main()
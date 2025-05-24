import time
import requests
import os
from datetime import datetime
import json
import glob
import RPi.GPIO as GPIO
from pymodbus.client import ModbusSerialClient
import math
import socket

# def load_dynamic_config():
#     try:
#         with open("config.json", "r") as f:
#             return json.load(f)
#     except Exception as e:
#         print("[WARN] Failed to load config.json:", e)
#         return {}


# === CONFIGURATION ===
SERVER = 'http://192.168.14.147:8000/'  # no trailing slash
EMAIL = 'redulgay@mail.com'
PASSWORD = 'redul'
NODE_ID = 3  # <-- ID of this node in the database
#

# === SETUP GPIO ===
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

            distance = 36 - (pulse_end - pulse_start) * 17150 
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

def read_modbus_sensors(client):
    if not client:
        return None, None
    try:
        # Baca 2 register dari alamat 0, slave ID 1
        result = client.read_holding_registers(address=0, count=2,slave=1)
        
        if result.isError():
            print(f"Modbus read error: {result}")
            return None, None
        
        if not hasattr(result, 'registers') or len(result.registers) < 2:
            print("Modbus returned incomplete data")
            print(f"Registers received: {getattr(result, 'registers', None)}")
            return None, None
        
        alkohol_raw = result.registers[0]
        foto = result.registers[1]

        # Konversi sensor alkohol dari nilai ADC ke voltase
        alkohol = alkohol_raw * (5.0 / 1023.0)
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

def calculate_rs(vcc, vrl, rl):
    try:
        return ((vcc - vrl) / vrl) * rl
    except ZeroDivisionError:
        return float('inf')

def calculate_ppm(rs, ro):
    if rs <= 0 or ro <= 0:
        return -1
    try:
        ratio = rs / ro
        log_ppm = -1.5512 * math.log10(ratio) + 2.5911
        return 10 ** log_ppm
    except:
        return -1
    
# === MAIN PROGRAM ===
def collect_sensor_data():
    modbus_client = setup_modbus()

    # Nilai kalibrasi dari hasil regresi
    faktor_kalibrasi = -102.23  # bit per gram
    offset_manual = 150  # Nilai offset manual
    VCC = 5.0
    RL = 10000
    RO = 5000   # Ganti jika kamu punya data kalibrasi

    suhu = read_temp()
    jarak = read_ultrasonik()
    # --- Perbaikan: baca Modbus dua kali, gunakan hasil kedua ---
    _ = read_modbus_sensors(modbus_client)  # abaikan hasil pertama
    alkohol, foto = read_modbus_sensors(modbus_client)  # gunakan hasil kedua
    nilai_load = average_read()

    # Hitung berat dengan formula yang diberikan
    berat = (nilai_load) / faktor_kalibrasi - offset_manual

    if alkohol is not None and alkohol > 0:
        rs = calculate_rs(VCC, alkohol, RL)
        alkohol = calculate_ppm(rs, RO)    

    # Buat data dalam format JSON
    data = {
        "timestamp": datetime.now().isoformat(),
        "temperature": round(suhu, 2),
        "alcohol": alkohol,
        # "alcohol": alkohol,
        "urine": foto,
        "berat": round(berat, 2),
        "tinggi": round(jarak, 2)
    }

    if modbus_client:
        modbus_client.close()

    return data

# === STEP 1: Authenticate and get token ===
def get_token():
    url = f"{SERVER}api-token-auth/"
    try:
        response = requests.post(url, json={"email": EMAIL, "password": PASSWORD})
        response.raise_for_status()  # This will raise an exception for 4xx/5xx status codes
        if response.status_code == 200:
            token = response.json()["token"]
            print("[INFO] Authenticated.")
            return token
    except requests.exceptions.RequestException as e:
        print("[ERROR] Failed to authenticate:", e)
    return None

# === STEP 2: Get own node info ===
def get_node_info(token):
    url = f"{SERVER}/api/nodes/{NODE_ID}/"
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print("[ERROR] Failed to fetch node info:", response.text)
        return None

# === STEP 3: set node status to reading ===
def busy_node_status(token):
    url = f"{SERVER}/api/nodes/{NODE_ID}/"
    headers = {"Authorization": f"Token {token}"}
    data = {"status": "reading"}
    response = requests.patch(url, json=data, headers=headers)
    if response.status_code == 200:
        print("[INFO] Node status set to reading.")
    else:
        print("[ERROR] Failed to set status:", response.text)

# === STEP 3: Send a fake reading ===
def send_reading(token, patient_id):
    # config = load_dynamic_config()
    url = f"{SERVER}/api/readings/"
    headers = {"Authorization": f"Token {token}"}

    # Collect sensor data
    data = collect_sensor_data()

    # Tambahkan patient_id ke data
    data["patient_id"] = patient_id

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print("[INFO] Reading sent.")
        return True
    else:
        print("[ERROR] Failed to send reading:", response.text)
        return False

# === STEP 4: Set node status back to idle ===
def reset_node_status(token):
    url = f"{SERVER}/api/nodes/{NODE_ID}/"
    headers = {"Authorization": f"Token {token}"}
    data = {"status": "available", "assigned_patient": None}
    response = requests.patch(url, json=data, headers=headers)
    if response.status_code == 200:
        print("[INFO] Node status reset to idle.")
    else:
        print("[ERROR] Failed to reset status:", response.text)

def wait_for_internet(host="8.8.8.8", port=53, timeout=3):
    """Tunggu hingga koneksi internet tersedia."""
    while True:
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            print("[INFO] Internet connection detected.")
            return
        except Exception:
            print("[INFO] Waiting for WiFi/internet connection...")
            time.sleep(2)

# === MAIN LOOP ===
def main():
    token = get_token()
    if not token:
        return

    while True:
        node_info = get_node_info(token)
        if not node_info:
            break  # Something went wrong

        status = node_info.get("status")
        patient_id = node_info.get("assigned_patient")

        if status == "assigned" and patient_id:
            busy_node_status(token)
            time.sleep(10)
            print(f"[INFO] Assigned patient {patient_id}. Starting reading...")
            success = send_reading(token, patient_id)
            if success:
                reset_node_status(token)
        else:
            print("[INFO] Waiting for job...")

        time.sleep(1)  # Wait before polling again

if __name__ == "__main__":
    wait_for_internet()
    main()

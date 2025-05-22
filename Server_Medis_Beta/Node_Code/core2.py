import time
import requests
import os
from datetime import datetime

import json

def load_dynamic_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print("[WARN] Failed to load config.json:", e)
        return {}

# === CONFIGURATION ===
SERVER = 'http://192.168.100.248:8000/'  # no trailing slash
EMAIL = 'redulgay@mail.com'
PASSWORD = 'redul'
NODE_ID = 3  # <-- ID of this node in the database

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
    config = load_dynamic_config()
    url = f"{SERVER}/api/readings/"
    headers = {"Authorization": f"Token {token}"}
    data = {
        "timestamp": datetime.now().isoformat(),  # or datetime.now().isoformat() if not using UTC
        "temperature" : config.get("temperature", 27),
        "alcohol": config.get("alcohol", 0.02),
        "urine": config.get("urine", 1),
        "berat": config.get("berat", 60),
        "tinggi": config.get("tinggi", 170),
        "patient_id": patient_id
    }
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
            time.sleep(5)
            print(f"[INFO] Assigned patient {patient_id}. Starting reading...")
            success = send_reading(token, patient_id)
            if success:
                reset_node_status(token)
        else:
            print("[INFO] Waiting for job...")

        time.sleep(5)  # Wait before polling again

if __name__ == "__main__":
    main()
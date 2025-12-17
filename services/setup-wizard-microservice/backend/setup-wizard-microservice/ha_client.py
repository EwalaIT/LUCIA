import requests
from config import HA_URL, HA_TOKEN

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

def get_states():
    url = f"{HA_URL.rstrip('/')}/api/states"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()

# Helper para extraer device_id de atributos si existe
def extract_device_id(state_obj):
    return state_obj.get("attributes", {}).get("device_id")

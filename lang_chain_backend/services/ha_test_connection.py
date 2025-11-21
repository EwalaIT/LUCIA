import requests
from config import settings

def test_ha_connection():
    url = f"{settings.ha_url}/api/states"
    headers = {
        "Authorization": f"Bearer {settings.ha_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        states = response.json()
        print(f"✅ Conexión exitosa. Primeros 5 estados de HA:\n{states[:5]}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con Home Assistant: {e}")

if __name__ == "__main__":
    test_ha_connection()

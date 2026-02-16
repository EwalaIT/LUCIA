import requests
import logging
from config import settings

logger = logging.getLogger(__name__)

HEADERS = {
    "Authorization": f"Bearer {settings.ha_token}",
    "Content-Type": "application/json",
}

def get_states():
    url = f"{settings.ha_url.rstrip('/')}/api/states"
    
    logger.info(f"[HA] Requesting states from: {url}")
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)

        logger.info(f"[HA] Response status: {r.status_code}")

        r.raise_for_status()

        data = r.json()

        logger.info(f"[HA] Retrieved {len(data)} states from Home Assistant")

        # Log parcial para debug sin inundar logs
        if data:
            logger.debug(f"[HA] First state sample: {data[0]}")

        return data

    except requests.exceptions.Timeout:
        logger.exception("[HA] Timeout while connecting to Home Assistant")
        raise

    except requests.exceptions.ConnectionError:
        logger.exception("[HA] Connection error to Home Assistant")
        raise

    except requests.exceptions.HTTPError as e:
        logger.exception(f"[HA] HTTP error: {e}")
        raise

    except Exception:
        logger.exception("[HA] Unexpected error while fetching states")
        raise

# Helper para extraer device_id de atributos si existe
def extract_device_id(state_obj):
    return state_obj.get("attributes", {}).get("device_id")

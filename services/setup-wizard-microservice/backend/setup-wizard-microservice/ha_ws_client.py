# ha_ws_client.py
import asyncio
import logging
from typing import Any, Dict, List, Optional
import aiohttp
from aiohttp import ClientConnectionError, WSServerHandshakeError, WSMsgType
from config import settings

logger = logging.getLogger(__name__)
# Simple TTL cache to avoid spam a HA: store results + expiry timestamp
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 30  # seconds

# Helper: create websocket url from HA_URL
def _ws_url():
    if settings.ha_url.startswith("https://"):
        return settings.ha_url.replace("https://", "wss://").rstrip("/") + "/api/websocket"
    if settings.ha_url.startswith("http://"):
        return settings.ha_url.replace("http://", "ws://").rstrip("/") + "/api/websocket"
    return settings.ha_url.rstrip("/") + "/api/websocket"

async def _ws_request(commands: List[Dict], timeout: int = 8) -> List[Dict]:
    """
    Opens a WS connection, authenticates, sends the list of commands (each with id),
    and waits for results for each id. Returns list of result dicts in same order as commands.
    Raises on auth fail / connection issues.
    """
    results_by_id = {}
    ws_url = _ws_url()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, timeout=timeout) as ws:
                # 1) receive auth_required
                msg = await ws.receive_json(timeout=timeout)
                if msg.get("type") == "auth_required":
                    # send auth
                    await ws.send_json({"type": "auth", "access_token": settings.ha_token})
                    auth_msg = await ws.receive_json(timeout=timeout)
                    if auth_msg.get("type") != "auth_ok":
                        raise RuntimeError(f"HA auth failed: {auth_msg}")
                elif msg.get("type") == "auth_ok":
                    # already
                    pass
                else:
                    # some HA versions may reply differently; accept auth_ok only
                    pass

                # send commands
                for cmd in commands:
                    await ws.send_json(cmd)

                # collect results until we have all ids or timeout
                pending_ids = {cmd["id"] for cmd in commands if "id" in cmd}
                # set a per-receive timeout (loop)
                import time
                deadline = time.time() + timeout
                while pending_ids and time.time() < deadline:
                    try:
                        r = await ws.receive(timeout=deadline - time.time())
                    except asyncio.TimeoutError:
                        break
                    if r.type == WSMsgType.TEXT:
                        try:
                            payload = r.json()
                        except Exception:
                            payload = None
                        if not isinstance(payload, dict):
                            continue
                        # If this is an auth error, raise
                        if payload.get("type") == "auth_invalid":
                            raise RuntimeError(f"Auth invalid: {payload}")
                        # If result for one of our ids:
                        if payload.get("type") == "result" and "id" in payload:
                            results_by_id[payload["id"]] = payload
                            pending_ids.discard(payload["id"])
                        # Some messages might be events etc. ignore
                    elif r.type == WSMsgType.ERROR:
                        raise RuntimeError("Websocket error: %s" % (r,))
                    else:
                        # ignore other message types
                        continue

                # prepare results in original order
                out = []
                for cmd in commands:
                    rid = cmd.get("id")
                    out.append(results_by_id.get(rid, {"id": rid, "type": "result", "success": False, "result": None}))
                return out
    except (ClientConnectionError, WSServerHandshakeError) as exc:
        raise RuntimeError(f"WS connect error: {exc}") from exc

# High-level fetchers
async def _fetch_area_registry() -> List[Dict]:
    # cache
    import time
    key = "areas"
    now = time.time()
    c = _CACHE.get(key)
    if c and c.get("expiry", 0) > now:
        return c["value"]
    commands = [{"id": 1, "type": "config/area_registry/list"}]
    res = await _ws_request(commands)
    resp = res[0]
    if resp.get("success"):
        value = resp.get("result", [])
        _CACHE[key] = {"value": value, "expiry": now + _CACHE_TTL}
        return value
    raise RuntimeError("Failed to fetch area registry: %s" % (resp,))

async def _fetch_device_registry() -> List[Dict]:
    import time
    key = "devices"
    now = time.time()
    c = _CACHE.get(key)
    if c and c.get("expiry", 0) > now:
        return c["value"]
    commands = [{"id": 2, "type": "config/device_registry/list"}]
    res = await _ws_request(commands)
    resp = res[0]
    if resp.get("success"):
        value = resp.get("result", [])
        _CACHE[key] = {"value": value, "expiry": now + _CACHE_TTL}
        return value
    raise RuntimeError("Failed to fetch device registry: %s" % (resp,))

async def _fetch_entity_registry() -> List[Dict]:
    import time
    key = "entities"
    now = time.time()
    c = _CACHE.get(key)
    if c and c.get("expiry", 0) > now:
        return c["value"]
    commands = [{"id": 3, "type": "config/entity_registry/list"}]
    res = await _ws_request(commands)
    resp = res[0]
    if resp.get("success"):
        value = resp.get("result", [])
        _CACHE[key] = {"value": value, "expiry": now + _CACHE_TTL}
        return value
    raise RuntimeError("Failed to fetch entity registry: %s" % (resp,))

# Public sync-friendly wrappers
def get_ha_areas() -> List[Dict]:
    """Synchronous wrapper returning area list from HA WS."""
    return asyncio.run(_fetch_area_registry())

def get_ha_devices() -> List[Dict]:
    return asyncio.run(_fetch_device_registry())

def get_ha_entities() -> List[Dict]:
    return asyncio.run(_fetch_entity_registry())

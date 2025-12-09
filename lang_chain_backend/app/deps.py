# app/deps.py
"""
Dependency module for authentication and access control (dummy mode).

This module provides:
- A dummy MCP-compatible Bearer token dependency using APIKeyHeader.
- No real validation is performed; all requests pass through.
"""

from __future__ import annotations
import logging
from typing import Optional

from fastapi import Security
from fastapi.security import APIKeyHeader

logger = logging.getLogger("auth.mcp")

# Define a generic Authorization header (Bearer token compatible)
api_key_header = APIKeyHeader(
    name="Authorization",
    auto_error=False,  # Prevent FastAPI from raising 403 automatically
)


async def require_mcp_access(authorization: Optional[str] = Security(api_key_header)) -> Optional[str]:
    """
    Dummy authentication dependency for FastMCP/LibreChat.

    - Accepts Authorization header if provided.
    - Does NOT validate the token (intentionally disabled).
    - Always returns successfully.

    Returns:
        The provided token string or None.
    """
    if authorization:
        logger.debug(f"[MCP AUTH] Received Authorization header: {authorization}")
    else:
        logger.debug("[MCP AUTH] No Authorization header provided.")

    # No validation performed. Token is returned as-is.
    return authorization

from flask import Blueprint
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from models import Base
from config import SQLALCHEMY_DATABASE_URI

import logging

logger = logging.getLogger(__name__)

# 1. Definir el Blueprint central (que se exportará a todos los módulos)
bp = Blueprint("api", __name__, url_prefix="/api")

# 2. Inicializar la DB una sola vez
engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False}
)
Base.metadata.create_all(engine)

def session():
    """Retorna una nueva sesión de SQLAlchemy."""
    return Session(engine)
try:
    from . import decisions
    from . import rules
    from . import setup

    logger.info("✅ All API blueprints (decisions, rules, setup) registered.")
except ImportError as e:
    logger.error("❌ Failed to import API module: %s", e)
    raise

import os
from dotenv import load_dotenv

load_dotenv()  # carga las variables de .env

DB_PATH = os.getenv("DB_PATH", "/home/jetson/Downloads/lang_chain_backend/db/agent_memory.db")
SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
HA_URL = os.getenv("HA_URL", "http://localhost:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "")
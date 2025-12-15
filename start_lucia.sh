#!/bin/bash

# Ruta base del proyecto principal
BASE_DIR="/home/jetson/Downloads/LUCIA"

# Ruta Setup Wizard
SETUP_WIZARD_BACKEND="$BASE_DIR/setup-wizard-microservice/backend"
SETUP_WIZARD_FRONTEND="$BASE_DIR/setup-wizard-microservice/frontend/setup-wizard-microservice"

# Ruta LangChain Backend (FastAPI)
LANGCHAIN_BACKEND="$BASE_DIR/lang_chain_backend"
LANGCHAIN_VENV="$LANGCHAIN_BACKEND/.venv/bin/activate"

# Directorios de logs
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$LOG_DIR"

echo "🚀 Iniciando Microservicios LUCIA..."
echo "Los logs estarán en: $LOG_DIR"
echo ""

# ============================================================
#   1) BACKEND ORIGINAL (npm run backend:dev)
# ============================================================
echo "🔧 Arrancando Backend principal..."
cd "$BASE_DIR" || exit 1
nohup npm run backend:dev > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$LOG_DIR/backend.pid"
echo "   ➤ Backend principal PID: $(cat $LOG_DIR/backend.pid)"
echo ""

# ============================================================
#   2) FRONTEND ORIGINAL (npm run dev)
# ============================================================
echo "💻 Arrancando Frontend principal..."
cd "$BASE_DIR/client" || exit 1
nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
echo $! > "$LOG_DIR/frontend.pid"
echo "   ➤ Frontend principal PID: $(cat $LOG_DIR/frontend.pid)"
echo ""

# ============================================================
#   3) BACKEND SETUP WIZARD (Flask + Poetry)
# ============================================================
echo "🧩 Arrancando Backend Setup Wizard (Flask + Poetry)..."
cd "$SETUP_WIZARD_BACKEND" || exit 1
nohup poetry run python setup-wizard-microservice/app.py \
    > "$LOG_DIR/setup_wizard_backend.log" 2>&1 &
echo $! > "$LOG_DIR/setup_wizard_backend.pid"
echo "   ➤ Backend Setup Wizard PID: $(cat $LOG_DIR/setup_wizard_backend.pid)"
echo ""

# ============================================================
#   4) FRONTEND SETUP WIZARD (Vite React)
# ============================================================
echo "🖥️  Arrancando Frontend Setup Wizard (Vite + React)..."
cd "$SETUP_WIZARD_FRONTEND" || exit 1
nohup npm run dev > "$LOG_DIR/setup_wizard_frontend.log" 2>&1 &
echo $! > "$LOG_DIR/setup_wizard_frontend.pid"
echo "   ➤ Frontend Setup Wizard PID: $(cat $LOG_DIR/setup_wizard_frontend.pid)"
echo ""

# ============================================================
#   5) BACKEND LANGCHAIN (FastAPI + uvicorn)
# ============================================================
echo "🤖 Arrancando LangChain Backend (FastAPI + uvicorn)..."
cd "$LANGCHAIN_BACKEND" || exit 1
. "$LANGCHAIN_VENV"
nohup uvicorn app.main:app --reload > "$LOG_DIR/langchain_backend.log" 2>&1 &
echo $! > "$LOG_DIR/langchain_backend.pid"
echo "   ➤ LangChain Backend PID: $(cat $LOG_DIR/langchain_backend.pid)"
echo ""

# ============================================================
#   RESUMEN
# ============================================================
echo "======================================================="
echo " ✅ LUCIA está ejecutándose en segundo plano."
echo "======================================================="
echo "   - Backend principal log: $LOG_DIR/backend.log"
echo "   - Frontend principal log: $LOG_DIR/frontend.log"
echo "   - Setup Wizard Backend log: $LOG_DIR/setup_wizard_backend.log"
echo "   - Setup Wizard Frontend log: $LOG_DIR/setup_wizard_frontend.log"
echo "   - LangChain Backend log: $LOG_DIR/langchain_backend.log"
echo ""
echo "Para detenerlos, ejecuta manualmente:"
echo "   kill \$(cat $LOG_DIR/backend.pid)"
echo "   kill \$(cat $LOG_DIR/frontend.pid)"
echo "   kill \$(cat $LOG_DIR/setup_wizard_backend.pid)"
echo "   kill \$(cat $LOG_DIR/setup_wizard_frontend.pid)"
echo "   kill \$(cat $LOG_DIR/langchain_backend.pid)"

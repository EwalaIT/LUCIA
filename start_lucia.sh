#!/bin/bash

# Ruta base del proyecto
BASE_DIR="/home/jetson/Downloads/LUCIA"

# Directorios de logs
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$LOG_DIR"

echo "🚀 Iniciando LUCIA Backend y Frontend..."
echo "Los logs estarán en: $LOG_DIR"

# Arrancar el backend
echo "🔧 Arrancando Backend..."
cd "$BASE_DIR" || exit 1
nohup npm run backend:dev > "$LOG_DIR/backend.log" 2>&1 &

# Guardar el PID
echo $! > "$LOG_DIR/backend.pid"

# Arrancar el frontend
echo "💻 Arrancando Frontend..."
cd "$BASE_DIR/client" || exit 1
nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &

# Guardar el PID
echo $! > "$LOG_DIR/frontend.pid"

echo ""
echo "✅ LUCIA está ejecutándose en segundo plano."
echo "   - Backend log: $LOG_DIR/backend.log"
echo "   - Frontend log: $LOG_DIR/frontend.log"
echo ""
echo "Para detenerlos, ejecuta:"
echo "   kill \$(cat $LOG_DIR/backend.pid)"
echo "   kill \$(cat $LOG_DIR/frontend.pid)"

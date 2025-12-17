# Base Node.js
FROM node:20

# -----------------------------
# Workdir
# -----------------------------
WORKDIR /app

# -----------------------------
# Copiar package.json + lock
# -----------------------------
COPY librechat/package*.json ./

# -----------------------------
# Instalación dependencias
# -----------------------------
RUN npm install

# -----------------------------
# Copiar todo el código
# -----------------------------
COPY librechat .

# -----------------------------
# Variables de entorno
# -----------------------------
# LibreChat backend las lee del .env
# No hardcodeamos nada aquí
ENV NODE_ENV=development

# -----------------------------
# Expose dev port
# -----------------------------
EXPOSE 3080

# -----------------------------
# CMD para desarrollo
# -----------------------------
CMD ["npm", "run", "dev"]

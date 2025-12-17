# Base Node.js
FROM node:20

# -----------------------------
# Workdir
# -----------------------------
WORKDIR /app

# -----------------------------
# Copiar package.json + lock
# -----------------------------
COPY librechat/client/package*.json ./

# -----------------------------
# Instalación dependencias
# -----------------------------
RUN npm ci

# -----------------------------
# Copiar todo el frontend
# -----------------------------
COPY librechat/client .

# -----------------------------
# Variables de entorno
# -----------------------------
ENV NODE_ENV=development
# VITE_API_URL se puede pasar desde .env en docker-compose

# -----------------------------
# Expose dev port
# -----------------------------
EXPOSE 5173

# -----------------------------
# CMD para desarrollo
# -----------------------------
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

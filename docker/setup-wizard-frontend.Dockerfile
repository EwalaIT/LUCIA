# -----------------------------
# Build stage
# -----------------------------
FROM node:20-alpine AS builder

WORKDIR /app

COPY services/setup_wizard_frontend/package*.json ./
RUN npm ci

COPY services/setup_wizard_frontend .
RUN npm run build

# -----------------------------
# Runtime stage
# -----------------------------
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Custom nginx config
COPY docker/nginx/setup-wizard.conf /etc/nginx/conf.d/default.conf

# Static files
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

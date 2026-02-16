# -----------------------------
# Build stage
# -----------------------------
FROM node:20-alpine AS builder

ARG VITE_SETUP_WIZARD_API_BASE_URL
ENV VITE_SETUP_WIZARD_API_BASE_URL=$VITE_SETUP_WIZARD_API_BASE_URL

WORKDIR /app

COPY services/setup-wizard-microservice/frontend/setup-wizard-microservice/package*.json ./
RUN npm ci

COPY services/setup-wizard-microservice/frontend/setup-wizard-microservice .
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

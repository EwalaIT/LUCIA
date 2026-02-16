FROM node:20-slim

RUN apt-get update && apt-get install -y python3 make g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY librechat/ ./

RUN npm install --legacy-peer-deps

RUN npm run build:packages

WORKDIR /app/client

ARG VITE_SETUP_WIZARD_BASE_URL
ENV VITE_SETUP_WIZARD_BASE_URL=$VITE_SETUP_WIZARD_BASE_URL

RUN npm install

RUN npm run build

EXPOSE 3090

CMD ["npm", "run", "preview-prod", "--", "--host", "0.0.0.0"]

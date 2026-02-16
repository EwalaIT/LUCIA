FROM node:20-slim

RUN apt-get update && apt-get install -y python3 make g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY librechat/ ./

RUN npm install --legacy-peer-deps

RUN npm run build:packages


WORKDIR /app/client

RUN npm install

RUN npm run build

WORKDIR /app

ENV NODE_ENV=development
EXPOSE 3080

CMD ["npm", "run", "backend:dev"]

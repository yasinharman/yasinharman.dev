# syntax=docker/dockerfile:1

# ---------- Build stage ----------
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Build-time env vars (Vite gömme: build sırasında inject edilir)
ARG VITE_N8N_WEBHOOK_URL
ENV VITE_N8N_WEBHOOK_URL=$VITE_N8N_WEBHOOK_URL

RUN npm run build

# ---------- Production stage ----------
FROM nginx:1.27-alpine AS runner

RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# Stage 1: сборка
# При лимите Docker Hub: docker login или переопределите образ: --build-arg NODE_IMAGE=...
ARG NODE_IMAGE=node:20-alpine
FROM ${NODE_IMAGE} AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Для деплоя за одним доменом: API на том же origin (/api). Переопределите при сборке при необходимости.
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Stage 2: раздача статики + nginx (прокси /api на backend)
ARG NGINX_IMAGE=nginx:alpine
FROM ${NGINX_IMAGE}

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

#!/bin/bash
# Скрипт деплоя на VPS (Ubuntu). Запускать из корня репозитория: ./deploy/deploy.sh
set -e

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Создайте файл .env (см. deploy/.env.production.example и deploy/DEPLOY.md)"
  exit 1
fi

echo "Сборка и запуск контейнеров..."
docker compose up -d --build

echo "Готово. Проверка: docker compose ps"
docker compose ps

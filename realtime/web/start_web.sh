#!/bin/bash
cd "$(dirname "$0")"

# Активируем виртуальное окружение
if [ ! -d "../venv" ]; then
    echo "Виртуальное окружение не найдено. Создаем..."
    cd ..
    python3 -m venv venv
    cd web
fi

source ../venv/bin/activate

# Устанавливаем зависимости для веб-сервера
echo "Установка зависимостей..."
pip install -q -r requirements.txt

# Загружаем переменные из .env файла
if [ -f ../.env ]; then
    set -a
    source ../.env
    set +a
    echo "Креды загружены из ../.env файла"
else
    echo "⚠️  Файл .env не найден! Создайте его в директории realtime/"
    echo "Используйте ../.env.example как шаблон"
    exit 1
fi

echo ""
echo "========================================="
echo "🎙️  Запуск веб-интерфейса голосового агента"
echo "========================================="
echo ""
echo "Веб-интерфейс будет доступен по адресу:"
echo "http://localhost:5000"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo ""

# Запускаем веб-сервер
python app.py

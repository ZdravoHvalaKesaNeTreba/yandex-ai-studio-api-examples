#!/bin/bash
cd "$(dirname "$0")"

# Активируем виртуальное окружение
source venv/bin/activate

# Загружаем переменные из .env файла
if [ -f .env ]; then
    # Загружаем переменные, игнорируя комментарии и пустые строки
    set -a
    source .env
    set +a
    echo "Креды загружены из .env файла"
else
    echo "Файл .env не найден! Создайте его на основе .env.example"
    exit 1
fi

echo "Запуск голосового агента..."
echo ""

# Запускаем голосового агента  
python voice_agent.py

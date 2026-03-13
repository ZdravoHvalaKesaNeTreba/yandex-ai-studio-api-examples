#!/bin/bash

# Активируем виртуальное окружение
source venv/bin/activate

# Экспортируем креды
export YANDEX_CLOUD_FOLDER_ID='your_folder_id_here'
export YANDEX_CLOUD_API_KEY='your_api_key_here'

# Запускаем голосового агента
python voice_agent.py

# Голосовой агент Yandex AI Studio

Демонстрационный голосовой агент с использованием Realtime API от Yandex AI Studio.

## Возможности

- 🎤 Голосовой ввод с микрофона
- 🔊 Голосовой вывод (синтез речи)
- 🤖 Интеграция с ассистентом Yandex AI
- 🛠️ Поддержка инструментов:
  - `get_weather` - получение погоды (демо-функция)
  - `web_search` - поиск в интернете
  - `file_search` - поиск по файлам (требуется Vector Store)

## Требования

- Python 3.10+
- Микрофон и колонки/наушники
- API ключ Yandex Cloud
- Folder ID из Yandex Cloud

## Установка

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Скопируйте файл `.env.example` в `.env` и заполните свои данные:

```bash
cp .env.example .env
```

3. Откройте файл `voice_agent.py` и замените значения переменных:
   - `YANDEX_CLOUD_FOLDER_ID` - ID вашего каталога в Yandex Cloud
   - `YANDEX_CLOUD_API_KEY` - ваш API ключ
   - `VECTOR_STORE_ID` (опционально) - ID векторного хранилища для file_search

## Как получить креды

1. **Folder ID**: 
   - Откройте [консоль Yandex Cloud](https://console.cloud.yandex.ru/)
   - Выберите ваш каталог
   - Скопируйте ID каталога из URL или настроек

2. **API Key**:
   - Перейдите в раздел [API ключи](https://console.cloud.yandex.ru/iam/api-keys)
   - Создайте новый API ключ
   - Скопируйте полученный ключ

3. **Vector Store ID** (опционально):
   - Для использования функции `file_search` создайте векторное хранилище в AI Studio
   - Подробнее в [документации](https://aistudio.yandex.ru/docs/ru/ai-studio/operations/agents/create-voice-agent.html)

## Запуск

```bash
python voice_agent.py
```

или

```bash
python3 voice_agent.py
```

⚠️ **Важно**: Используйте наушники, чтобы избежать самопрерываний агента (когда микрофон улавливает звук из динамиков).

## Использование

После запуска программа подключится к Realtime API и начнет слушать ваш голос:

1. Говорите в микрофон
2. Система автоматически определит, когда вы закончили говорить (Server VAD)
3. Агент ответит голосом

### Примеры запросов

- "Какая погода в Москве?" - вызовет функцию `get_weather`
- "Расскажи новости" - вызовет функцию `web_search`
- "Чеклист для путешествий" - вызовет функцию `file_search` (если настроен Vector Store)

## Выход

Нажмите `Ctrl+C` для завершения работы.

## Документация

- [Создание голосового агента](https://aistudio.yandex.ru/docs/ru/ai-studio/operations/agents/create-voice-agent.html)
- [Realtime API Reference](https://aistudio.yandex.ru/docs/ru/ai-studio/api-ref/realtime/)

#!/usr/bin/env python3
"""
Проверка аутентификации в Yandex Cloud API
"""
import os
import sys

YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID", "your_folder_id_here")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY", "your_api_key_here")

WSS_URL = (
    f"wss://rest-assistant.api.cloud.yandex.net/v1/realtime/openai"
    f"?model=gpt://{YANDEX_CLOUD_FOLDER_ID}/speech-realtime-250923"
)

HEADERS = {"Authorization": f"api-key {YANDEX_CLOUD_API_KEY}"}


async def test_auth():
    """Тестирование аутентификации"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WSS_URL, headers=HEADERS, heartbeat=20.0) as ws:
                print("✅ Аутентификация успешна!")
                print(f"Подключено к: {WSS_URL}")
                
                # Получаем первое сообщение от сервера
                msg = await ws.receive()
                print(f"Ответ сервера: {msg.data}")
                
    except Exception as e:
        print(f"❌ Ошибка аутентификации: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    
    print(f"Тестирование аутентификации...")
    print(f"Folder ID: {YANDEX_CLOUD_FOLDER_ID}")
    print(f"API Key: {'*' * 20}{YANDEX_CLOUD_API_KEY[-10:]}")
    print()
    
    asyncio.run(test_auth())

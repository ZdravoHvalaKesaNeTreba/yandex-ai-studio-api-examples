#!/usr/bin/env python3
"""
Веб-сервер для голосового агента с WebSocket поддержкой
"""
import asyncio
import base64
import json
import logging
import os
from threading import Thread

import aiohttp
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Инициализация Flask приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandex-voice-agent-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Креденшалы из переменных окружения (опционально)
DEFAULT_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID", "")
DEFAULT_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY", "")


def get_wss_url(folder_id):
    """Построение URL для WebSocket"""
    return (
        f"wss://rest-assistant.api.cloud.yandex.net/v1/realtime/openai"
        f"?model=gpt://{folder_id}/speech-realtime-250923"
    )


def get_headers(api_key):
    """Получение заголовков для авторизации"""
    return {"Authorization": f"api-key {api_key}"}


# Вспомогательные функции
def b64_decode(s: str) -> bytes:
    return base64.b64decode(s)


def b64_encode(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


# Хранилище активных сессий
active_sessions = {}


class VoiceSession:
    """Класс для управления голосовой сессией"""
    
    def __init__(self, sid, folder_id, api_key):
        self.sid = sid
        self.folder_id = folder_id
        self.api_key = api_key
        self.ws = None
        self.running = False
        self.wss_url = get_wss_url(folder_id)
        self.headers = get_headers(api_key)
        
    async def setup_session(self):
        """Настройка сессии"""
        await self.ws.send_json({
            "type": "session.update",
            "session": {
                "instructions": (
                    "Ты голосовой ассистент Яндекса. Помогаешь с ответами на вопросы. "
                    "Отвечаешь кратко и по делу. "
                    "Если просят рассказать новости — используй функцию web_search. "
                    "Если спрашивают о погоде — вызывай функцию get_weather."
                ),
                "modalities": ["audio"],
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "silence_duration_ms": 500,
                },
                "voice": "dasha",
                "tools": []
            }
        })
    
    async def handle_messages(self):
        """Обработка сообщений от сервера"""
        try:
            async for msg in self.ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                    
                message = json.loads(msg.data)
                msg_type = message.get("type")
                
                # Отправляем сообщение клиенту
                socketio.emit('server_message', {
                    'type': msg_type,
                    'data': message
                }, room=self.sid)
                
                # Обработка конкретных типов сообщений
                if msg_type == "conversation.item.input_audio_transcription.completed":
                    transcript = message.get("transcript", "")
                    if transcript:
                        socketio.emit('transcript', {
                            'text': transcript,
                            'speaker': 'user'
                        }, room=self.sid)
                
                elif msg_type == "response.output_text.delta":
                    delta = message.get("delta", "")
                    if delta:
                        socketio.emit('response_text', {
                            'text': delta
                        }, room=self.sid)
                
                elif msg_type == "response.output_audio.delta":
                    delta = message.get("delta")
                    if delta:
                        socketio.emit('audio_data', {
                            'audio': delta
                        }, room=self.sid)
                
                elif msg_type == "input_audio_buffer.speech_started":
                    socketio.emit('speech_started', {}, room=self.sid)
                
                elif msg_type == "error":
                    logger.error(f"Ошибка сервера: {message}")
                    socketio.emit('error', {
                        'message': message.get('error', {}).get('message', 'Unknown error')
                    }, room=self.sid)
                    
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщений: {e}")
        finally:
            self.running = False
            socketio.emit('session_ended', {}, room=self.sid)
    
    async def start(self):
        """Запуск сессии"""
        try:
            self.running = True
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(self.wss_url, headers=self.headers, heartbeat=20.0) as ws:
                    self.ws = ws
                    logger.info(f"Сессия {self.sid} подключена к Realtime API")
                    
                    await self.setup_session()
                    await self.handle_messages()
                    
        except Exception as e:
            logger.error(f"Ошибка в сессии {self.sid}: {e}")
            socketio.emit('error', {
                'message': str(e)
            }, room=self.sid)
        finally:
            self.running = False
            if self.sid in active_sessions:
                del active_sessions[self.sid]
    
    async def send_audio(self, audio_data):
        """Отправка аудио на сервер"""
        if self.ws and self.running:
            await self.ws.send_json({
                "type": "input_audio_buffer.append",
                "audio": audio_data
            })


def run_async_session(session):
    """Запуск асинхронной сессии в отдельном потоке"""
    asyncio.run(session.start())


async def validate_credentials(folder_id, api_key):
    """Проверка валидности креденшалов"""
    try:
        wss_url = get_wss_url(folder_id)
        headers = get_headers(api_key)
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(wss_url, headers=headers, heartbeat=20.0, timeout=aiohttp.ClientTimeout(total=10)) as ws:
                # Отправляем простой запрос
                await ws.send_json({
                    "type": "session.update",
                    "session": {
                        "modalities": ["audio"],
                        "voice": "dasha"
                    }
                })
                
                # Ждем ответ
                msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    # Если получили корректный ответ - креды валидны
                    if data.get("type") in ["session.created", "session.updated"]:
                        return True, "Креденшалы валидны"
                
                return False, "Неожиданный ответ от сервера"
                
    except asyncio.TimeoutError:
        return False, "Время ожидания истекло. Проверьте креденшалы."
    except aiohttp.ClientConnectorError:
        return False, "Не удалось подключиться к серверу. Проверьте интернет соединение."
    except Exception as e:
        error_msg = str(e)
        if "UNAUTHENTICATED" in error_msg or "api key" in error_msg.lower():
            return False, "Неверный API ключ"
        elif "NXDOMAIN" in error_msg or "nodename" in error_msg:
            return False, "Сервер недоступен. Проверьте URL API."
        else:
            return False, f"Ошибка: {error_msg}"


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/validate', methods=['POST'])
def validate():
    """Валидация креденшалов"""
    data = request.get_json()
    folder_id = data.get('folder_id', '').strip()
    api_key = data.get('api_key', '').strip()
    
    if not folder_id or not api_key:
        return jsonify({
            'valid': False,
            'message': 'Folder ID и API Key обязательны'
        }), 400
    
    # Запускаем проверку в отдельном event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    is_valid, message = loop.run_until_complete(validate_credentials(folder_id, api_key))
    loop.close()
    
    return jsonify({
        'valid': is_valid,
        'message': message
    })


@socketio.on('connect')
def handle_connect():
    """Обработка подключения клиента"""
    sid = request.sid
    logger.info(f"Клиент подключен: {sid}")
    emit('connected', {'sid': sid})


@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения клиента"""
    sid = request.sid
    logger.info(f"Клиент отключен: {sid}")
    
    if sid in active_sessions:
        active_sessions[sid].running = False
        del active_sessions[sid]


@socketio.on('start_session')
def handle_start_session(data=None):
    """Запуск новой голосовой сессии"""
    sid = request.sid
    
    if sid in active_sessions:
        emit('error', {'message': 'Сессия уже запущена'})
        return
    
    if not data:
        emit('error', {'message': 'Креденшалы не предоставлены'})
        return
    
    folder_id = data.get('folder_id', '').strip()
    api_key = data.get('api_key', '').strip()
    
    if not folder_id or not api_key:
        emit('error', {'message': 'Креденшалы не предоставлены'})
        return
    
    session = VoiceSession(sid, folder_id, api_key)
    active_sessions[sid] = session
    
    # Запускаем сессию в отдельном потоке
    thread = Thread(target=run_async_session, args=(session,))
    thread.daemon = True
    thread.start()
    
    emit('session_started', {'status': 'ok'})


@socketio.on('audio_data')
def handle_audio_data(data):
    """Обработка аудио данных от клиента"""
    sid = request.sid
    
    if sid not in active_sessions:
        emit('error', {'message': 'Сессия не запущена'})
        return
    
    session = active_sessions[sid]
    audio_base64 = data.get('audio')
    
    if audio_base64 and session.ws:
        # Создаем новый event loop для отправки
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(session.send_audio(audio_base64))
        loop.close()


@socketio.on('stop_session')
def handle_stop_session():
    """Остановка голосовой сессии"""
    sid = request.sid
    
    if sid in active_sessions:
        active_sessions[sid].running = False
        del active_sessions[sid]
        emit('session_stopped', {'status': 'ok'})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Запуск веб-сервера на порту {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)

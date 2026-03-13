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
from flask import Flask, render_template, request
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

# Креденшалы из переменных окружения
YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID", "")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY", "")

assert YANDEX_CLOUD_FOLDER_ID and YANDEX_CLOUD_API_KEY, (
    "YANDEX_CLOUD_FOLDER_ID и YANDEX_CLOUD_API_KEY обязательны"
)

WSS_URL = (
    f"wss://rest-assistant.api.cloud.yandex.net/v1/realtime/openai"
    f"?model=gpt://{YANDEX_CLOUD_FOLDER_ID}/speech-realtime-250923"
)

HEADERS = {"Authorization": f"api-key {YANDEX_CLOUD_API_KEY}"}


# Вспомогательные функции
def b64_decode(s: str) -> bytes:
    return base64.b64decode(s)


def b64_encode(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


# Хранилище активных сессий
active_sessions = {}


class VoiceSession:
    """Класс для управления голосовой сессией"""
    
    def __init__(self, sid):
        self.sid = sid
        self.ws = None
        self.running = False
        
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
                async with session.ws_connect(WSS_URL, headers=HEADERS, heartbeat=20.0) as ws:
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


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


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
def handle_start_session():
    """Запуск новой голосовой сессии"""
    sid = request.sid
    
    if sid in active_sessions:
        emit('error', {'message': 'Сессия уже запущена'})
        return
    
    session = VoiceSession(sid)
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

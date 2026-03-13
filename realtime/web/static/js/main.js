// Главный класс для управления голосовым интерфейсом
class VoiceAssistant {
    constructor() {
        this.socket = null;
        this.mediaRecorder = null;
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        this.isRecording = false;
        this.isSessionActive = false;
        this.credentials = null;
        
        this.initElements();
        this.initSocket();
        this.initEventListeners();
        this.checkCredentials();
    }
    
    initElements() {
        this.micButton = document.getElementById('micButton');
        this.stopButton = document.getElementById('stopButton');
        this.settingsButton = document.getElementById('settingsButton');
        this.statusBadge = document.getElementById('statusBadge');
        this.dotsContainer = document.getElementById('dotsContainer');
        this.transcriptArea = document.getElementById('transcriptArea');
        this.settingsModal = document.getElementById('settingsModal');
        this.settingsForm = document.getElementById('settingsForm');
        this.formStatus = document.getElementById('formStatus');
        this.saveButton = document.getElementById('saveButton');
    }
    
    initSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Подключено к серверу');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Отключено от сервера');
            this.updateStatus('Отключено', 'error');
            this.stopSession();
        });
        
        this.socket.on('session_started', () => {
            console.log('Сессия запущена');
            this.isSessionActive = true;
        });
        
        this.socket.on('session_ended', () => {
            console.log('Сессия завершена');
            this.stopSession();
        });
        
        this.socket.on('transcript', (data) => {
            console.log('Транскрипт:', data);
            if (data.speaker === 'user') {
                this.addMessage(data.text, 'user');
            }
        });
        
        this.socket.on('response_text', (data) => {
            console.log('Ответ ассистента:', data.text);
            this.addMessage(data.text, 'assistant');
        });
        
        this.socket.on('audio_data', (data) => {
            this.playAudioChunk(data.audio);
        });
        
        this.socket.on('speech_started', () => {
            console.log('Пользователь начал говорить');
            this.dotsContainer.classList.remove('listening');
            this.dotsContainer.classList.add('speaking');
        });
        
        this.socket.on('error', (data) => {
            console.error('Ошибка:', data.message);
            this.showError(data.message);
            this.stopSession();
        });
    }
    
    initEventListeners() {
        this.micButton.addEventListener('click', () => {
            if (!this.credentials) {
                this.showSettings();
                return;
            }
            if (!this.isRecording) {
                this.startRecording();
            }
        });
        
        this.stopButton.addEventListener('click', () => {
            this.stopSession();
        });
        
        this.settingsButton.addEventListener('click', () => {
            this.showSettings();
        });
        
        this.settingsForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveCredentials();
        });
        
        // Закрытие модального окна по клику на фон
        this.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.settingsModal) {
                this.hideSettings();
            }
        });
    }
    
    checkCredentials() {
        // Проверяем сохраненные креденшалы в localStorage
        const savedCreds = localStorage.getItem('yandex_credentials');
        if (savedCreds) {
            try {
                this.credentials = JSON.parse(savedCreds);
                this.validateCredentials();
            } catch (e) {
                console.error('Ошибка парсинга креденшалов:', e);
                this.showSettings();
            }
        } else {
            this.showSettings();
        }
    }
    
    async validateCredentials() {
        this.updateStatus('Проверка подключения...', 'checking');
        
        try {
            const response = await fetch('/api/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.credentials)
            });
            
            const result = await response.json();
            
            if (result.valid) {
                this.updateStatus('Готов к работе');
                this.settingsButton.style.display = 'flex';
                this.micButton.disabled = false;
            } else {
                this.updateStatus('Ошибка подключения', 'error');
                this.showSettings();
                this.showFormStatus(result.message, 'error');
            }
        } catch (error) {
            console.error('Ошибка валидации:', error);
            this.updateStatus('Ошибка подключения', 'error');
            this.showSettings();
            this.showFormStatus('Не удалось подключиться к серверу', 'error');
        }
    }
    
    async saveCredentials() {
        const folderId = document.getElementById('folderId').value.trim();
        const apiKey = document.getElementById('apiKey').value.trim();
        
        if (!folderId || !apiKey) {
            this.showFormStatus('Заполните все поля', 'error');
            return;
        }
        
        // Показываем лоадер
        this.saveButton.disabled = true;
        this.saveButton.querySelector('.btn-text').textContent = 'Проверка...';
        this.saveButton.querySelector('.btn-loader').style.display = 'block';
        this.formStatus.style.display = 'none';
        
        try {
            const response = await fetch('/api/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    folder_id: folderId,
                    api_key: apiKey
                })
            });
            
            const result = await response.json();
            
            if (result.valid) {
                // Сохраняем креденшалы
                this.credentials = {
                    folder_id: folderId,
                    api_key: apiKey
                };
                localStorage.setItem('yandex_credentials', JSON.stringify(this.credentials));
                
                // Показываем успех
                this.showFormStatus('✓ Подключение успешно!', 'success');
                
                // Закрываем модальное окно через 1 секунду
                setTimeout(() => {
                    this.hideSettings();
                    this.updateStatus('Готов к работе');
                    this.settingsButton.style.display = 'flex';
                    this.micButton.disabled = false;
                }, 1000);
            } else {
                this.showFormStatus(result.message, 'error');
            }
        } catch (error) {
            console.error('Ошибка сохранения:', error);
            this.showFormStatus('Не удалось подключиться к серверу', 'error');
        } finally {
            this.saveButton.disabled = false;
            this.saveButton.querySelector('.btn-text').textContent = 'Проверить и сохранить';
            this.saveButton.querySelector('.btn-loader').style.display = 'none';
        }
    }
    
    showSettings() {
        this.settingsModal.classList.add('show');
        
        // Загружаем сохраненные значения
        if (this.credentials) {
            document.getElementById('folderId').value = this.credentials.folder_id || '';
            document.getElementById('apiKey').value = this.credentials.api_key || '';
        }
        
        this.formStatus.style.display = 'none';
    }
    
    hideSettings() {
        this.settingsModal.classList.remove('show');
    }
    
    showFormStatus(message, type) {
        this.formStatus.textContent = message;
        this.formStatus.className = `form-status ${type}`;
        this.formStatus.style.display = 'block';
    }
    
    showError(message) {
        alert(message);
    }
    
    async startRecording() {
        if (!this.credentials) {
            this.showSettings();
            return;
        }
        
        try {
            // Запрашиваем доступ к микрофону
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                } 
            });
            
            // Запускаем сессию на сервере с креденшалами
            this.socket.emit('start_session', this.credentials);
            
            // Инициализируем AudioContext для обработки аудио
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });
            
            const source = this.audioContext.createMediaStreamSource(stream);
            const processor = this.audioContext.createScriptProcessor(4096, 1, 1);
            
            source.connect(processor);
            processor.connect(this.audioContext.destination);
            
            processor.onaudioprocess = (e) => {
                if (!this.isRecording) return;
                
                const inputData = e.inputBuffer.getChannelData(0);
                const pcm16 = this.floatTo16BitPCM(inputData);
                const base64Audio = this.arrayBufferToBase64(pcm16);
                
                // Отправляем аудио на сервер
                this.socket.emit('audio_data', { audio: base64Audio });
            };
            
            this.mediaRecorder = { stream, processor, source };
            this.isRecording = true;
            
            // Обновляем UI
            this.micButton.classList.add('listening');
            this.micButton.style.display = 'none';
            this.stopButton.style.display = 'flex';
            this.dotsContainer.classList.add('listening');
            this.updateStatus('Слушаю...', 'listening');
            
            // Очищаем transcript area
            this.clearTranscripts();
            
        } catch (error) {
            console.error('Ошибка при доступе к микрофону:', error);
            alert('Не удалось получить доступ к микрофону. Пожалуйста, разрешите доступ.');
        }
    }
    
    stopSession() {
        // Останавливаем запись
        if (this.mediaRecorder) {
            if (this.mediaRecorder.stream) {
                this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
            if (this.mediaRecorder.processor) {
                this.mediaRecorder.processor.disconnect();
            }
            if (this.mediaRecorder.source) {
                this.mediaRecorder.source.disconnect();
            }
            this.mediaRecorder = null;
        }
        
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        // Останавливаем сессию на сервере
        if (this.isSessionActive) {
            this.socket.emit('stop_session');
        }
        
        this.isRecording = false;
        this.isSessionActive = false;
        
        // Обновляем UI
        this.micButton.classList.remove('listening');
        this.micButton.style.display = 'flex';
        this.stopButton.style.display = 'none';
        this.dotsContainer.classList.remove('listening', 'speaking');
        this.updateStatus('Готов к работе');
    }
    
    updateStatus(text, state = '') {
        const statusText = this.statusBadge.querySelector('.status-text');
        statusText.textContent = text;
        
        this.statusBadge.classList.remove('active', 'listening', 'error', 'checking');
        if (state) {
            this.statusBadge.classList.add(state);
        }
    }
    
    addMessage(text, speaker) {
        // Удаляем placeholder если есть
        const placeholder = this.transcriptArea.querySelector('.transcript-placeholder');
        if (placeholder) {
            placeholder.remove();
        }
        
        // Ищем последнее сообщение от этого же спикера
        const messages = this.transcriptArea.querySelectorAll('.transcript-message');
        const lastMessage = messages[messages.length - 1];
        
        if (lastMessage && lastMessage.classList.contains(speaker)) {
            // Добавляем к существующему сообщению
            lastMessage.textContent += ' ' + text;
        } else {
            // Создаем новое сообщение
            const messageDiv = document.createElement('div');
            messageDiv.className = `transcript-message ${speaker}`;
            messageDiv.textContent = text;
            this.transcriptArea.appendChild(messageDiv);
        }
        
        // Прокручиваем вниз
        this.transcriptArea.scrollTop = this.transcriptArea.scrollHeight;
    }
    
    clearTranscripts() {
        this.transcriptArea.innerHTML = '<div class="transcript-placeholder">Говорите...</div>';
    }
    
    async playAudioChunk(base64Audio) {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        try {
            // Декодируем base64 в ArrayBuffer
            const binaryString = atob(base64Audio);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            // Конвертируем PCM16 в Float32
            const pcm16 = new Int16Array(bytes.buffer);
            const float32 = new Float32Array(pcm16.length);
            for (let i = 0; i < pcm16.length; i++) {
                float32[i] = pcm16[i] / 32768.0;
            }
            
            // Создаем AudioBuffer
            const audioBuffer = this.audioContext.createBuffer(1, float32.length, 44100);
            audioBuffer.getChannelData(0).set(float32);
            
            // Воспроизводим
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            source.start();
            
            // Анимация точек при воспроизведении
            this.dotsContainer.classList.remove('listening');
            this.dotsContainer.classList.add('speaking');
            
            source.onended = () => {
                this.dotsContainer.classList.remove('speaking');
                if (this.isRecording) {
                    this.dotsContainer.classList.add('listening');
                }
            };
            
        } catch (error) {
            console.error('Ошибка при воспроизведении аудио:', error);
        }
    }
    
    // Конвертация Float32Array в Int16Array (PCM16)
    floatTo16BitPCM(float32Array) {
        const buffer = new ArrayBuffer(float32Array.length * 2);
        const view = new DataView(buffer);
        let offset = 0;
        
        for (let i = 0; i < float32Array.length; i++, offset += 2) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }
        
        return buffer;
    }
    
    // Конвертация ArrayBuffer в Base64
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    const assistant = new VoiceAssistant();
    
    // Предотвращение масштабирования на iOS
    document.addEventListener('gesturestart', (e) => {
        e.preventDefault();
    });
});

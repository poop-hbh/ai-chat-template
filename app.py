# -*- coding: utf-8 -*-
"""
Простой сайт с чатом. Всё в одном файле.
Запуск: python app.py
Открыть: http://127.0.0.1:8000
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from collections import defaultdict
from time import time
import uvicorn

app = FastAPI(title="AI Site")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ---------- Rate limiting ----------
RATE_LIMIT = 10
RATE_WINDOW = 60
_rate_store = defaultdict(list)

def check_rate(ip: str) -> bool:
    now = time()
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < RATE_WINDOW]
    if len(_rate_store[ip]) >= RATE_LIMIT:
        return False
    _rate_store[ip].append(now)
    return True


class ChatMessage(BaseModel):
    message: str = Field(..., max_length=2000)


HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Site</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: system-ui, sans-serif;
            background: #0f0f0f;
            color: #eee;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        header {
            padding: 16px;
            background: #1a1a1a;
            border-bottom: 1px solid #333;
            font-weight: 600;
        }
        #chat {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .msg {
            max-width: 70%;
            padding: 10px 14px;
            border-radius: 12px;
            line-height: 1.4;
            word-wrap: break-word;
        }
        .user { align-self: flex-end; background: #2b5278; }
        .bot  { align-self: flex-start; background: #2a2a2a; }
        #input-area {
            display: flex;
            padding: 12px;
            background: #1a1a1a;
            border-top: 1px solid #333;
            gap: 8px;
        }
        #input {
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #333;
            background: #0f0f0f;
            color: #eee;
            font-size: 15px;
            outline: none;
        }
        #input:focus { border-color: #2b5278; }
        button {
            padding: 12px 20px;
            border-radius: 8px;
            border: none;
            background: #2b5278;
            color: #fff;
            font-size: 15px;
            cursor: pointer;
        }
        button:hover { background: #3a6b9a; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
    </style>
</head>
<body>
    <header>🤖 AI Site — тестовая версия</header>
    <div id="chat">
        <div class="msg bot">Привет! Я пока заглушка. Напиши что-нибудь — я отвечу.</div>
    </div>
    <div id="input-area">
        <input id="input" type="text" placeholder="Напиши сообщение..." autocomplete="off" maxlength="2000">
        <button id="send">Отправить</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const send = document.getElementById('send');

        function addMsg(text, cls) {
            const div = document.createElement('div');
            div.className = 'msg ' + cls;
            div.textContent = text;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        async function sendMessage() {
            const text = input.value.trim();
            if (!text) return;
            addMsg(text, 'user');
            input.value = '';
            send.disabled = true;

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000);

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: text}),
                    signal: controller.signal
                });
                if (res.status === 429) {
                    addMsg('Слишком много сообщений. Подожди минуту.', 'bot');
                    return;
                }
                if (!res.ok) {
                    addMsg('Ошибка сервера: ' + res.status, 'bot');
                    return;
                }
                const data = await res.json();
                addMsg(data.reply, 'bot');
            } catch (e) {
                if (e.name === 'AbortError') {
                    addMsg('Превышено время ожидания. Попробуй ещё раз.', 'bot');
                } else {
                    addMsg('Ошибка: ' + e.message, 'bot');
                }
            } finally {
                clearTimeout(timeoutId);
                send.disabled = false;
                input.focus();
            }
        }

        send.addEventListener('click', sendMessage);
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(msg: ChatMessage, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests")

    user_text = msg.message.strip()
    if not user_text:
        return {"reply": "Пустое сообщение. Напиши что-нибудь."}

    # --- ЗАГЛУШКА ---
    # Здесь позже можно вызвать настоящий LLM API (Groq, OpenAI, Ollama и т.д.)
    try:
        reply = f"Ты написал: «{user_text}». Я пока заглушка, но скоро стану умным."
    except Exception as e:
        print(f"[ERROR] {e}")
        reply = "Внутренняя ошибка. Попробуй ещё раз."
    # ----------------

    return {"reply": reply}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

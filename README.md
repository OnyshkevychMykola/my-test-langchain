# Медичний асистент — пошук та аналіз ліків

Бот для пошуку за фото або опису та детального аналізу ліків.

## Можливості

- **Find** — розпізнавання препарату за фото (галерея або камера).
- **Ask** — питання про ліки (з валідацією нетипових питань).
- **Авторизація** — вхід через Google, дані користувача та розмови зберігаються.
- **Розмови** — сайдбар у стилі ChatGPT: список розмов, нова розмова, контекстне вікно (останні N повідомлень).
- Промпти в `prompts/*.md`; бекенд FastAPI; UI React + Tailwind.

## База даних (SQLite)

- **users** — користувачі (google_id, email, name, avatar_url).
- **conversations** — розмови (user_id, title, updated_at).
- **messages** — повідомлення (conversation_id, role, content). Для історії в LLM використовується контекстне вікно (останні 20 повідомлень).

Файл БД: `medical_assistant.db` у корені проєкту.

## Запуск

### 1. Налаштування

Скопіюйте `.env.example` в `.env` і заповніть:

- `OPENAI_API_KEY` — ключ OpenAI.
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — OAuth у [Google Cloud Console](https://console.cloud.google.com/apis/credentials). Додайте redirect URI: `http://localhost:8000/auth/google/callback`.
- Опційно: `JWT_SECRET`, `FRONTEND_URL` (за замовчуванням `http://localhost:5173`).

### 2. Бекенд

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

API: `http://127.0.0.1:8000`

### 3. React-інтерфейс

```bash
cd frontend
npm install
npm run dev
```

Відкрити: `http://localhost:5173`. Логін — «Увійти через Google»; після входу доступні розмови в сайдбарі.

### 4. Streamlit (старий UI, без авторизації)

```bash
streamlit run app.py
```

## Структура

- `prompts/` — системні промпти (Markdown).
- `db.py` — SQLite: users, conversations, messages, контекстне вікно.
- `auth.py` — Google OAuth, JWT.
- `chains.py` — логіка агента та валідація питань.
- `api.py` — FastAPI: auth, conversations, chat (ask/find).
- `frontend/` — React: логін, сайдбар з розмовами, чат.

## Buy

Режим **Buy** поки не реалізований.

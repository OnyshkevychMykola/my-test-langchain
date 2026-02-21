# Медичний асистент — пошук та аналіз ліків

Веб-додаток для пошуку та детального аналізу ліків за фото або текстовим запитом. Підтримує авторизацію через Google, збереження розмов та контекстне вікно для історії діалогу.

---

## Опис проєкту

- **Find** — розпізнавання препарату за зображенням (галерея або камера).
- **Ask** — текстові питання про ліки з валідацією нетипових запитів.
- **Авторизація** — вхід через Google OAuth; дані користувача та розмови зберігаються в SQLite.
- **Розмови** — сайдбар у стилі чату: список розмов, створення нової (одна порожня за раз), видалення. Контекстне вікно — останні 20 повідомлень для LLM.

Стек: **бекенд** — Python, FastAPI, LangChain, SQLite; **фронтенд** — React, TypeScript, Vite, Tailwind CSS.

---

## Вимоги

- **Бекенд:** Python 3.10+, ключ OpenAI, облікові дані Google OAuth (Client ID / Secret).
- **Фронтенд:** Node.js 18+ (npm або yarn).

Детальні списки залежностей — у розділах «Бекенд» та «Фронтенд» нижче.

---

## Запуск (коротко)

1. Налаштувати `.env` у корені проєкту (див. [Бекенд](#бекенд)).
2. Запустити бекенд: `uvicorn api:app --reload` (порт 8000).
3. Запустити фронтенд: `cd frontend && npm install && npm run dev` (порт 5173).
4. Відкрити в браузері `http://localhost:5173`, увійти через Google.

Повні інструкції — нижче в окремих розділах для бекенду та фронтенду.

---

## Бекенд

API та логіка чату (FastAPI, LangChain, SQLite, Google OAuth).

### Вимоги (Python)

- Python 3.10+
- Залежності з `requirements.txt` у корені проєкту:
  - `fastapi`, `uvicorn`, `python-multipart`
  - `langchain`, `langchain-openai`, `langchain-community`
  - `python-dotenv`, `httpx`, `PyJWT`
  - та інші з файлу.

### Змінні середовища (.env)

У корені проєкту створіть `.env` (можна скопіювати з `.env.example`):

| Змінна | Опис |
|--------|------|
| `OPENAI_API_KEY` | Ключ API OpenAI (обовʼязково). |
| `GOOGLE_CLIENT_ID` | Google OAuth 2.0 Client ID. |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 2.0 Client Secret. |
| `JWT_SECRET` | Секрет для JWT (опційно; якщо немає — генерується при старті). |
| `FRONTEND_URL` | URL фронтенду після логіну (за замовч. `http://localhost:5173`). |
| `API_BASE_URL` | Публічна URL бекенду для OAuth redirect (за замовч. `http://localhost:8000`). |

У [Google Cloud Console](https://console.cloud.google.com/apis/credentials) створіть OAuth 2.0 Client (тип «Веб-додаток») і додайте **Authorized redirect URI**:  
`http://localhost:8000/auth/google/callback` (або ваш `API_BASE_URL` + `/auth/google/callback`).

### Встановлення та запуск

```bash
# У корені проєкту (там, де api.py та requirements.txt)
pip install -r requirements.txt
uvicorn api:app --reload
```

- API: **http://127.0.0.1:8000**
- Документація: http://127.0.0.1:8000/docs

### Основні файли

| Файл | Призначення |
|------|-------------|
| `api.py` | FastAPI: auth, conversations, chat (ask/find). |
| `chains.py` | LangChain-агент, промпти, валідація медичних питань. |
| `db.py` | SQLite: users, conversations, messages, контекстне вікно. |
| `auth.py` | Google OAuth, JWT. |
| `prompts/*.md` | Системні промпти (Markdown). |

База даних: файл **`medical_assistant.db`** у корені проєкту (створюється при першому запиті).

---

## Фронтенд

React-інтерфейс: логін через Google, сайдбар з розмовами, чат (Find / Ask).

### Вимоги (Node.js)

- Node.js 18+
- Залежності з `frontend/package.json`: React 18, Vite, TypeScript, Tailwind CSS.

### Встановлення та запуск

```bash
cd frontend
npm install
npm run dev
```

- Додаток: **http://localhost:5173**
- Запити до API йдуть через proxy `/api` → `http://127.0.0.1:8000` (у `vite.config.ts`).

Перед першим запуском має бути запущений бекенд (порт 8000).

### Скрипти

| Команда | Опис |
|--------|------|
| `npm run dev` | Режим розробки з hot reload. |
| `npm run build` | Збірка для продакшену в `dist/`. |
| `npm run preview` | Локальний перегляд збірки. |

Детальніше — у **frontend/README.md**.

---

## Структура проєкту

```
.
├── api.py              # FastAPI-додаток
├── auth.py             # Google OAuth, JWT
├── chains.py           # Логіка агента та промпти
├── db.py               # SQLite
├── requirements.txt
├── .env.example
├── prompts/            # Системні промпти (.md)
├── frontend/           # React-додаток
│   ├── README.md       # Інструкції для фронтенду
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── auth.tsx
│       ├── ChatPage.tsx
│       ├── LoginPage.tsx
│       └── ...
├── app.py              # Streamlit (старий UI, опційно)
└── README.md           # Цей файл
```

---

## Streamlit (опційно)

Старий інтерфейс без авторизації та збереження розмов:

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Режим Buy

Поки не реалізований.

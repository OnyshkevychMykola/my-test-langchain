# Медичний асистент — пошук та аналіз ліків

Веб-додаток для пошуку та детального аналізу ліків за фото або текстовим запитом. Підтримує авторизацію через Google, збереження розмов, контекстне вікно для історії діалогу та пошук аптек на карті.

---

## Опис проєкту

- **Find** — розпізнавання препарату за зображенням (галерея або камера).
- **Ask** — текстові питання про ліки з валідацією нетипових запитів.
- **Аптеки** — пошук найближчих аптек на інтерактивній карті (OpenStreetMap / Leaflet).
- **Авторизація** — вхід через Google OAuth; дані користувача та розмови зберігаються в SQLite.
- **Розмови** — сайдбар у стилі чату: список розмов, створення нової (одна порожня за раз), видалення. Контекстне вікно — останні 20 повідомлень для LLM.

Стек: **бекенд** — Python, FastAPI, LangChain, SQLite; **фронтенд** — React, TypeScript, Vite, Tailwind CSS, Leaflet.

---

## Вимоги

- **Бекенд:** Python 3.10+, ключ OpenAI, облікові дані Google OAuth (Client ID / Secret).
- **Фронтенд:** Node.js 18+ (npm або yarn).

Детальні списки залежностей — у розділах «Бекенд» та «Фронтенд» нижче.

---

## Запуск (коротко)

1. Налаштувати `backend/.env` (див. [Бекенд](#бекенд)).
2. Запустити бекенд: `cd backend && uvicorn api:app --reload` (порт 8000).
3. Запустити фронтенд: `cd frontend && npm install && npm run dev` (порт 5173).
4. Відкрити в браузері `http://localhost:5173`, увійти через Google.

Повні інструкції — нижче в окремих розділах для бекенду та фронтенду.

---

## Бекенд

API та логіка чату (FastAPI, LangChain, SQLite, Google OAuth). Всі Python-файли знаходяться у папці `backend/`.

### Вимоги (Python)

- Python 3.10+
- Залежності з `backend/requirements.txt`:
  - `fastapi`, `uvicorn`, `python-multipart`
  - `langchain`, `langchain-openai`, `langchain-community`
  - `python-dotenv`, `httpx`, `PyJWT`
  - та інші з файлу.

### Змінні середовища (.env)

У папці `backend/` створіть `.env` (можна скопіювати з `backend/.env.example`):

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
cd backend
pip install -r requirements.txt
uvicorn api:app --reload
```

- API: **http://127.0.0.1:8000**
- Документація: http://127.0.0.1:8000/docs

### Основні файли

| Файл | Призначення |
|------|-------------|
| `backend/api.py` | FastAPI: auth, conversations, chat (ask/find). |
| `backend/chains.py` | LangChain-агент, промпти, валідація медичних питань. |
| `backend/db.py` | SQLite: users, conversations, messages, контекстне вікно. |
| `backend/auth.py` | Google OAuth, JWT. |
| `backend/prompts/*.md` | Системні промпти (Markdown). |

База даних: файл **`medical_assistant.db`** у папці `backend/` (створюється при першому запиті).

---

## Фронтенд

React-інтерфейс: логін через Google, сайдбар з розмовами, чат (Find / Ask), карта аптек.

### Вимоги (Node.js)

- Node.js 18+
- Залежності з `frontend/package.json`: React 18, Vite, TypeScript, Tailwind CSS, react-leaflet.

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
├── backend/                # Python-бекенд
│   ├── api.py              # FastAPI-додаток
│   ├── auth.py             # Google OAuth, JWT
│   ├── chains.py           # Логіка агента та промпти
│   ├── db.py               # SQLite
│   ├── app.py              # Streamlit (старий UI, опційно)
│   ├── requirements.txt
│   ├── .env.example
│   └── prompts/            # Системні промпти (.md)
│       ├── system.md
│       ├── image_analysis.md
│       └── validation.md
├── frontend/               # React-додаток
│   ├── README.md           # Інструкції для фронтенду
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── auth.tsx
│       ├── ChatPage.tsx
│       ├── LoginPage.tsx
│       ├── PharmaciesPage.tsx  # Карта аптек
│       └── ...
└── README.md               # Цей файл
```

---

## Streamlit (опційно)

Старий інтерфейс без авторизації та збереження розмов:

```bash
cd backend
pip install -r requirements.txt
streamlit run app.py
```

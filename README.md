# Медичний асистент — пошук та аналіз ліків

Бот для пошуку за фото або опису та детального аналізу ліків.

## Можливості

- **Find** — розпізнавання препарату за фото (галерея або камера).
- **Ask** — питання про ліки (з валідацією нетипових питань).
- Промпти винесені в MD-файли у `prompts/`.
- Backend: FastAPI; UI: React + Tailwind (чат з перемикачем режимів).

## Запуск

### 1. Бекенд (обов’язково)

```bash
# в корені проєкту
pip install -r requirements.txt
# .env з OPENAI_API_KEY
uvicorn api:app --reload
```

API: `http://127.0.0.1:8000`

### 2. React-інтерфейс (чат Find / Ask)

```bash
cd frontend
npm install
npm run dev
```

Відкрити: `http://localhost:5173`. Запити йдуть на бекенд через proxy `/api` → `:8000`.

### 3. Streamlit (старий UI)

```bash
streamlit run app.py
```

## Структура

- `prompts/` — системні промпти в Markdown: `system.md`, `image_analysis.md`, `validation.md`.
- `chains.py` — логіка агента, валідація медичних питань, завантаження промптів.
- `api.py` — FastAPI: `POST /chat/ask`, `POST /chat/find`.
- `frontend/` — React-чат з режимами Find та Ask.

## Buy

Режим **Buy** поки не реалізований (за планом).

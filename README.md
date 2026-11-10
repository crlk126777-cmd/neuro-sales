# NeuroSales — AI-помощник продаж GRANARWOOD

Полноценное MVP веб-приложения для учёта клиентских заявок и подготовки ответов клиентам.

## Возможности
- Авторизация администратора с подписанной сессией.
- Создание, просмотр, поиск, изменение статуса и удаление заявок.
- Панель показателей: всего, новые, в работе, успешные сделки.
- AI Sales Assistant: генерация ответа через OpenAI API (если задан `OPENAI_API_KEY`); автономный шаблонный режим без ключа.
- SQLite — постоянное хранение данных.
- REST API и интерактивная документация Swagger.
- Защитные HTTP-заголовки, валидация входных данных, секреты через переменные окружения.
- Docker Compose для запуска.

## Быстрый запуск (Windows / macOS / Linux)
1. Установите Python 3.11 или новее.
2. Создайте виртуальное окружение:
   `python -m venv .venv`
3. Активируйте его:
   Windows: `.venv\\Scripts\\activate`
   macOS/Linux: `source .venv/bin/activate`
4. Установите зависимости: `pip install -r requirements.txt`
5. Скопируйте `.env.example` в `.env` и задайте собственные `APP_PASSWORD` и `TOKEN_SECRET`. Для настоящей AI-генерации дополнительно укажите `OPENAI_API_KEY`; без него приложение работает в автономном демонстрационном режиме.
6. Запустите: `uvicorn app.main:app --reload`
7. Откройте http://127.0.0.1:8000

Для локального учебного запуска без настройки `.env` пароль по умолчанию: `change-this-password`. Перед публикацией обязательно замените его.

## Тесты
`pytest -q`

## Docker
`docker compose up --build`

## API
- `POST /api/login`
- `GET /api/leads`
- `POST /api/leads`
- `PATCH /api/leads/{id}`
- `DELETE /api/leads/{id}`
- `GET /api/stats`
- `POST /api/ai/reply`
- `GET /health`
- `GET /api/docs` — Swagger UI

Все маршруты `/api`, кроме авторизации, требуют Bearer-токен.

## Структура
- `app/main.py` — backend, API, авторизация и база SQLite
- `app/static/` — frontend
- `tests/` — автоматические тесты
- `.env.example` — пример конфигурации
- `Dockerfile`, `docker-compose.yml` — контейнеризация

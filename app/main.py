import os, hmac, hashlib, secrets, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "data" / "neurosales.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
APP_PASSWORD = os.getenv("APP_PASSWORD", "change-this-password")
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "change-this-token-secret")
TOKEN_TTL_HOURS = 12

app = FastAPI(title="NeuroSales", version="1.0.0", docs_url="/api/docs")
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

class LoginData(BaseModel):
    password: str = Field(min_length=8, max_length=200)

class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=5, max_length=40)
    product: str = Field(min_length=2, max_length=120)
    volume: str = Field(default="", max_length=80)
    source: str = Field(default="Сайт", max_length=50)
    comment: str = Field(default="", max_length=1000)
    status: str = Field(default="Новая", max_length=30)

class LeadUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    phone: Optional[str] = Field(default=None, min_length=5, max_length=40)
    product: Optional[str] = Field(default=None, min_length=2, max_length=120)
    volume: Optional[str] = Field(default=None, max_length=80)
    source: Optional[str] = Field(default=None, max_length=50)
    comment: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = Field(default=None, max_length=30)

class AIRequest(BaseModel):
    lead_id: int
    tone: str = Field(default="Деловой", max_length=30)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, phone TEXT NOT NULL, product TEXT NOT NULL,
            volume TEXT DEFAULT '', source TEXT DEFAULT 'Сайт',
            comment TEXT DEFAULT '', status TEXT DEFAULT 'Новая',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )
        """)
        conn.commit()

init_db()

def make_token(password: str) -> str:
    if not hmac.compare_digest(password, APP_PASSWORD):
        raise HTTPException(status_code=401, detail="Неверный пароль")
    expires = str(int((datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)).timestamp()))
    nonce = secrets.token_hex(8)
    payload = f"{expires}.{nonce}"
    signature = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"

def require_auth(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    token = authorization[7:]
    try:
        expires, nonce, signature = token.split(".", 2)
        payload = f"{expires}.{nonce}"
        expected = hmac.new(TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expires) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=401, detail="Сессия недействительна или истекла")
    return True

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'"
    return response

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "app" / "static" / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "service": "NeuroSales"}

@app.post("/api/login")
def login(data: LoginData):
    return {"access_token": make_token(data.password), "token_type": "bearer"}

@app.get("/api/leads")
def list_leads(_: bool = Depends(require_auth)):
    with db() as conn:
        rows = conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]

@app.post("/api/leads", status_code=201)
def create_lead(data: LeadCreate, _: bool = Depends(require_auth)):
    now = datetime.now(timezone.utc).isoformat()
    values = data.model_dump()
    with db() as conn:
        cur = conn.execute("""INSERT INTO leads
        (name, phone, product, volume, source, comment, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (values["name"].strip(), values["phone"].strip(), values["product"].strip(),
         values["volume"].strip(), values["source"].strip(), values["comment"].strip(),
         values["status"], now, now))
        conn.commit()
        row = conn.execute("SELECT * FROM leads WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)

@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: int, data: LeadUpdate, _: bool = Depends(require_auth)):
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if not changes:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")
    changes["updated_at"] = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        exists = conn.execute("SELECT id FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        assignments = ", ".join(f"{key}=?" for key in changes)
        conn.execute(f"UPDATE leads SET {assignments} WHERE id=?", (*changes.values(), lead_id))
        conn.commit()
        row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    return dict(row)

@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: int, _: bool = Depends(require_auth)):
    with db() as conn:
        cur = conn.execute("DELETE FROM leads WHERE id=?", (lead_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
    return {"deleted": True}

@app.get("/api/stats")
def stats(_: bool = Depends(require_auth)):
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        fresh = conn.execute("SELECT COUNT(*) FROM leads WHERE status='Новая'").fetchone()[0]
        in_work = conn.execute("SELECT COUNT(*) FROM leads WHERE status='В работе'").fetchone()[0]
        won = conn.execute("SELECT COUNT(*) FROM leads WHERE status='Успешно'").fetchone()[0]
    return {"total": total, "new": fresh, "in_work": in_work, "won": won}

@app.post("/api/ai/reply")
def ai_reply(data: AIRequest, _: bool = Depends(require_auth)):
    with db() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id=?", (data.lead_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    lead = dict(row)
    greeting = f"Здравствуйте, {lead['name']}!"
    # Если задан ключ OpenAI, используем настоящую LLM; без ключа работает автономный шаблонный режим.
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        import httpx
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        prompt = (
            "Ты — менеджер по продажам компании GRANARWOOD, производителя пиломатериалов. "
            "Составь короткий, конкретный и вежливый ответ клиенту на русском языке. "
            "Не выдумывай цены, наличие, характеристики и сроки. Если данных не хватает, задай уточняющий вопрос. "
            f"Тон: {data.tone}. Клиент: {lead['name']}. Телефон: {lead['phone']}. "
            f"Запрос: {lead['product']}. Объём: {lead['volume'] or 'не указан'}. "
            f"Комментарий: {lead['comment'] or 'нет'}."
        )
        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5},
                timeout=25.0,
            )
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"].strip()
            return {"reply": f"{greeting}\\n\\n{answer}\\n\\nС уважением, команда GRANARWOOD.", "mode": "ai"}
        except Exception:
            raise HTTPException(status_code=502, detail="Не удалось получить ответ от AI-сервиса. Проверьте API-ключ и соединение.")
    body = (f"Спасибо за интерес к продукции GRANARWOOD. По вашему запросу: "
            f"{lead['product']}. Объём: {lead['volume'] or 'уточним'}. "
            "Подберём оптимальный вариант по размерам, сорту и срокам поставки.")
    if data.tone == "Дружелюбный":
        body = (f"Рады вашему обращению! Поможем подобрать {lead['product']} "
                f"под вашу задачу. По объёму {lead['volume'] or 'давайте уточним'} "
                "и срокам быстро сориентируем.")
    elif data.tone == "Краткий":
        body = (f"Получили заявку на {lead['product']}. Уточните, пожалуйста, "
                "нужные размеры и сроки — подготовим предложение.")
    return {"reply": f"{greeting}\\n\\n{body}\\n\\nС уважением, команда GRANARWOOD.", "mode": "template"}

@app.get("/api/docs-link")
def docs_link(_: bool = Depends(require_auth)):
    return {"url": "/api/docs"}

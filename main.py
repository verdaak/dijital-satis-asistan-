import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from database import init_db, get_schema_description, get_db_stats
from seed_data import seed_database
from agent import SalesAnalystAgent

load_dotenv()

ACTIVE_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")

app = FastAPI(
    title="Kozmetik Mağazası Satış Analiz Sistemi (Text-to-SQL)",
    description="Tek Agent (SalesAnalystAgent) ve Tek Tool (run_sql_query) Mimarisi",
    version="1.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None  # [{ "role": "user"|"assistant", "content": "..." }]
    api_key: Optional[str] = None


class ApiKeyRequest(BaseModel):
    api_key: str


def format_chart_data(sql_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not sql_data or sql_data.get("status") != "success" or not sql_data.get("rows"):
        return None

    rows = sql_data["rows"]
    columns = sql_data["columns"]

    if len(rows) < 1 or len(columns) < 2:
        return None

    label_col = None
    value_col = None

    first_row = rows[0]
    for col in columns:
        val = first_row[col]
        if isinstance(val, str) and label_col is None:
            label_col = col
        elif isinstance(val, (int, float)) and value_col is None:
            value_col = col

    if not label_col:
        label_col = columns[0]
    if not value_col and len(columns) > 1:
        value_col = columns[1]

    if not label_col or not value_col:
        return None

    labels = []
    values = []

    for row in rows[:15]:
        labels.append(str(row.get(label_col, "")))
        try:
            val = float(row.get(value_col, 0))
            values.append(val)
        except (ValueError, TypeError):
            values.append(0.0)

    return {
        "labels": labels,
        "values": values,
        "label_name": label_col.replace("_", " ").title(),
        "value_name": value_col.replace("_", " ").title()
    }


@app.on_event("startup")
def startup_event():
    stats = get_db_stats()
    if stats.get("sales", 0) == 0:
        seed_database()


@app.post("/api-key")
def set_api_key(req: ApiKeyRequest):
    global ACTIVE_API_KEY
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API Key boş olamaz.")
    
    ACTIVE_API_KEY = key
    os.environ["GEMINI_API_KEY"] = key
    os.environ["GOOGLE_API_KEY"] = key
    os.environ["ANTHROPIC_API_KEY"] = key
    return {"status": "success", "message": "API Key başarıyla güncellendi!"}


@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    """
    Kullanıcının doğal dildeki sorusunu ve son 5-10 mesajlık konuşma geçmişini alan ana endpoint.
    """
    global ACTIVE_API_KEY
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Soru metni boş olamaz.")

    key_to_use = request.api_key.strip() if request.api_key and request.api_key.strip() else ACTIVE_API_KEY

    agent = SalesAnalystAgent(api_key=key_to_use)
    # Sohbet hafızasını (history) agent'a aktar
    result = agent.run(request.message.strip(), history=request.history)

    chart_payload = format_chart_data(result.get("data"))
    result["chart_data"] = chart_payload
    result["has_api_key"] = bool(key_to_use)

    return result


@app.get("/schema")
def schema_endpoint():
    return {
        "schema": get_schema_description(),
        "stats": get_db_stats(),
        "has_api_key": bool(ACTIVE_API_KEY)
    }


@app.get("/health")
def health_endpoint():
    return {
        "status": "ok",
        "database": "connected",
        "has_api_key": bool(ACTIVE_API_KEY),
        "stats": get_db_stats()
    }


static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

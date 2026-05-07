from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import gradio as gr

from database import (
    init_db, create_quote, get_quote, get_all_quotes,
    update_quote, delete_quote, get_stats,
)
from gradio_app import build_gradio_app
from scraper import run_scraper


class QuoteCreate(BaseModel):
    text: str
    author: str
    tags: str = ""

    model_config = {"json_schema_extra": {
        "example": {
            "text": "The only way to do great work is to love what you do.",
            "author": "Steve Jobs",
            "tags": "work,passion,life",
        }
    }}


class QuoteUpdate(BaseModel):
    text: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[str] = None


class QuoteResponse(BaseModel):
    id: int
    text: str
    author: str
    tags: str
    source: str
    created_at: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if not get_all_quotes(limit=1):
        print("📡 초기 데이터 크롤링 시작...")
        result = run_scraper(max_per_cat=20)
        print(f"✅ 크롤링 완료: {result}")
    yield


app = FastAPI(
    title="📚 Quotes API",
    description=(
        "quotes.toscrape.com 기반 격언 관리 및 분석 시스템\n\n"
        "- **CRUD**: 격언 생성/조회/수정/삭제\n"
        "- **Gradio UI**: `/ui` 에서 접근\n"
        "- **통계**: `/api/v1/stats`"
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.post(
    "/api/v1/quotes",
    response_model=QuoteResponse,
    status_code=201,
    summary="격언 생성",
    tags=["Quotes"],
)
def api_create(body: QuoteCreate):
    return create_quote(body.text, body.author, body.tags, source="manual")


@app.get(
    "/api/v1/quotes",
    response_model=list[QuoteResponse],
    summary="격언 목록 조회",
    tags=["Quotes"],
)
def api_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    author: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
):
    return get_all_quotes(skip=skip, limit=limit, author=author, tag=tag, keyword=keyword)


@app.get(
    "/api/v1/quotes/{quote_id}",
    response_model=QuoteResponse,
    summary="격언 단건 조회",
    tags=["Quotes"],
)
def api_get(quote_id: int):
    q = get_quote(quote_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"ID={quote_id} not found")
    return q


@app.patch(
    "/api/v1/quotes/{quote_id}",
    response_model=QuoteResponse,
    summary="격언 수정",
    tags=["Quotes"],
)
def api_update(quote_id: int, body: QuoteUpdate):
    q = update_quote(quote_id, body.text, body.author, body.tags)
    if not q:
        raise HTTPException(status_code=404, detail=f"ID={quote_id} not found")
    return q


@app.delete(
    "/api/v1/quotes/{quote_id}",
    status_code=204,
    summary="격언 삭제",
    tags=["Quotes"],
)
def api_delete(quote_id: int):
    if not delete_quote(quote_id):
        raise HTTPException(status_code=404, detail=f"ID={quote_id} not found")


@app.get(
    "/api/v1/stats",
    summary="통계 조회",
    tags=["Analytics"],
)
def api_stats():
    return get_stats()


@app.post(
    "/api/v1/crawl",
    summary="크롤링 실행",
    tags=["Admin"],
)
def api_crawl(
    categories: list[str] = Query(default=["love", "life", "inspirational"]),
    max_per_cat: int = Query(20, ge=1, le=50),
):
    return run_scraper(categories=categories, max_per_cat=max_per_cat)


gradio_ui = build_gradio_app()
app = gr.mount_gradio_app(app, gradio_ui, path="/ui")


if __name__ == "__main__":
    import uvicorn
    from pyngrok import ngrok

    ngrok.set_auth_token("3DLjDQ6LW7vqkBPs4PGK3Xv5UWa_ja3mJEYhWMXciHUhwpMN")
    tunnel = ngrok.connect(7860)
    print(f"\n🌐 외부 URL: {tunnel.public_url}")
    print(f"📋 Swagger: {tunnel.public_url}/docs")
    print(f"🎨 Gradio UI: {tunnel.public_url}/ui\n")

    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)
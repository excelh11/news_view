import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class ChatSearchRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    max_results: int = Field(default=3, ge=1, le=30)


class Article(BaseModel):
    title: str
    url: str
    source: str
    published_at: Optional[str] = None


class ChatSearchResponse(BaseModel):
    original_ko: str
    translated_en: str
    articles: List[Article]


def translate_ko_to_en(text: str) -> str:
    """
    Free LLM-based translation via local Ollama (no paid API keys).

    Prereq:
      - Install Ollama and run it
      - Pull a model once (e.g. `ollama pull llama3.2`)

    Config:
      - OLLAMA_URL (default http://127.0.0.1:11434)
      - OLLAMA_MODEL (default llama3.2)
    """
    base = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")

    prompt = (
        "Translate the following Korean text to natural English for a news search query. "
        "Return ONLY the English translation, no quotes, no explanation.\n\n"
        f"Korean: {text}\nEnglish:"
    )

    # Prefer /api/generate for broad compatibility
    url = f"{base}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        out = (data.get("response") or "").strip()
        out = out.strip().strip('"').strip("'").strip()
        if not out:
            raise RuntimeError("empty translation")
        return out
    except requests.RequestException as e:
        raise RuntimeError(
            f"Ollama 호출 실패. Ollama 실행 여부/모델 다운로드를 확인하세요. ({e})"
        ) from e


def search_gdelt(query_en: str, max_results: int) -> List[Dict[str, Any]]:
    """
    Free news search using GDELT 2.1 Doc API (no API key).
    """
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query_en,
        "mode": "artlist",
        "format": "json",
        "maxrecords": str(max_results),
        "sort": "hybridrel",
    }
    resp = requests.get(
        base_url,
        params=params,
        timeout=15,
        headers={"User-Agent": "news_view/0.1 (local dev)"},
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("articles", []) or []


def search_google_news_rss(query_en: str, max_results: int) -> List[Article]:
    """
    Fallback free news search using Google News RSS (no API key).
    """
    url = "https://news.google.com/rss/search"
    params = {"q": query_en, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    resp = requests.get(
        url,
        params=params,
        timeout=15,
        headers={"User-Agent": "news_view/0.1 (local dev)"},
    )
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    channel = root.find("channel")
    if channel is None:
        return []

    out: List[Article] = []
    for item in channel.findall("item"):
        if len(out) >= max_results:
            break
        title = (item.findtext("title") or "").strip() or "(제목 없음)"
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip() or None

        source_el = item.find("source")
        source = "Google News"
        if source_el is not None:
            source = (source_el.text or source).strip() or source

        if link:
            out.append(Article(title=title, url=link, source=source, published_at=pub_date))

    return out


def _rss_query(q: str) -> str:
    """
    Make query more RSS-friendly (remove punctuation, keep it short).
    """
    q = q.strip()
    q = re.sub(r"[^\w\s]", " ", q, flags=re.UNICODE)
    q = re.sub(r"\s+", " ", q).strip()
    if len(q) > 120:
        q = q[:120].rsplit(" ", 1)[0].strip() or q[:120]
    return q


def _normalize_article(a: Dict[str, Any]) -> Article:
    title = (a.get("title") or "").strip() or "(제목 없음)"
    url = (a.get("url") or "").strip()
    source = (a.get("sourceCountry") or a.get("sourceCollection") or a.get("domain") or "GDELT").strip()

    published_at = a.get("seendate") or a.get("datetime") or a.get("date")
    if isinstance(published_at, str):
        published_at = published_at.strip() or None

    return Article(title=title, url=url, source=source, published_at=published_at)


app = FastAPI(title="news_view backend", version="0.1.0")

_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SEC = 60

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat-search", response_model=ChatSearchResponse)
def chat_search(req: ChatSearchRequest) -> ChatSearchResponse:
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    cache_key = f"{message}|{req.max_results}"
    cached = _cache.get(cache_key)
    now = time.time()
    if cached and now - float(cached.get("ts", 0)) < _CACHE_TTL_SEC:
        return ChatSearchResponse(
            original_ko=message,
            translated_en=str(cached.get("translated_en", "")),
            articles=list(cached.get("articles", [])),
        )

    try:
        translated = translate_ko_to_en(message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"translation failed: {e}") from e

    articles: List[Article] = []
    try:
        raw_articles = search_gdelt(translated, req.max_results)
        for a in raw_articles:
            try:
                norm = _normalize_article(a)
                if norm.url:
                    articles.append(norm)
            except Exception:
                continue
    except requests.HTTPError as e:
        # GDELT responded but with error (e.g. 429). We'll fallback to RSS.
        try:
            articles = search_google_news_rss(_rss_query(translated), req.max_results)
        except Exception as e2:
            raise HTTPException(
                status_code=502,
                detail=f"news search failed: {e2}",
            ) from e2
    except requests.RequestException as e:
        # GDELT connection/timeouts/etc. Fallback to RSS.
        try:
            articles = search_google_news_rss(_rss_query(translated), req.max_results)
        except Exception as e2:
            raise HTTPException(
                status_code=502,
                detail=f"news search failed: {e2}",
            ) from e2
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"news search failed: {e}") from e

    _cache[cache_key] = {"ts": now, "translated_en": translated, "articles": articles}

    return ChatSearchResponse(original_ko=message, translated_en=translated, articles=articles)


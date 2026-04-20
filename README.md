# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

## AI 챗봇(무료 LLM 기반) 뉴스 검색

React(Vite) 프론트에 파이썬(FastAPI) 백엔드를 붙여,
사용자가 입력한 **한글을 무료 로컬 LLM(Ollama)로 영어로 번역**한 뒤
**GDELT(무료, API Key 불필요)**에서 관련 뉴스 기사를 검색해 보여줍니다. (GDELT 실패 시 **Google News RSS**로 대체)

### 챗봇 흐름 (클래스 다이어그램)

아래는 **어느 React 컴포넌트에서 입력**이 들어가고, **어느 파이썬 파일**이 요청을 받아 **Ollama·외부 뉴스 소스**와 연결되는지 보여주는 클래스 다이어그램입니다.

```mermaid
classDiagram
  direction LR

  class NewsPage {
    <<React>>
    src/pages/NewsPage.jsx
  }

  class ChatbotNewsSearch {
    <<React>>
    src/components/ChatbotNewsSearch.jsx
    +사용자 입력
    +fetch POST /api/chat-search
  }

  class ViteConfig {
    <<Vite>>
    vite.config.js
    +server.proxy /api
  }

  class FastAPIApp {
    <<Python>>
    backend/main.py
    +app FastAPI
    +POST /api/chat-search
    +translate_ko_to_en()
    +search_gdelt()
    +search_google_news_rss()
  }

  class Ollama {
    <<로컬 LLM>>
    HTTP 127.0.0.1:11434
    +POST /api/generate
  }

  class GdeltApi {
    <<외부 API>>
    api.gdeltproject.org
  }

  class GoogleNewsRss {
    <<외부 RSS>>
    news.google.com/rss
  }

  NewsPage *-- ChatbotNewsSearch : 포함
  ChatbotNewsSearch --> ViteConfig : 브라우저 요청 /api/*
  ViteConfig --> FastAPIApp : 프록시 127.0.0.1:8000
  FastAPIApp --> Ollama : 한글 → 영어 번역
  FastAPIApp --> GdeltApi : 뉴스 검색(1차)
  FastAPIApp --> GoogleNewsRss : 뉴스 검색(폴백)
```

**요약:** 사용자는 `ChatbotNewsSearch`에 한글을 입력합니다 → Vite가 `/api/chat-search`를 `backend/main.py`(FastAPI)로 넘깁니다 → `main.py`가 Ollama에 번역을 요청한 뒤, GDELT(또는 폴백으로 Google News RSS)로 기사를 찾아 JSON으로 돌려줍니다.

### 실행 방법

프론트(React):

```bash
yarn dev
```

백엔드(FastAPI):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Ollama(무료 로컬 LLM) 준비:

```bash
# Ollama 설치 후 (새 터미널)
ollama pull llama3.2
ollama serve
```

기본 모델은 `llama3.2`이며, 환경변수로 바꿀 수 있습니다:

- `OLLAMA_MODEL` (예: `llama3.2`, `llama3.1`, 등)
- `OLLAMA_URL` (기본: `http://127.0.0.1:11434`)

프론트는 `vite.config.js` 프록시 설정으로 `/api/*` 요청을 `http://127.0.0.1:8000`으로 전달합니다.

### API

- `GET /api/health`: 상태 확인
- `POST /api/chat-search`: 한글 입력 → 번역 → 뉴스 검색

요청 예시:

```json
{ "message": "한국 반도체 수출 전망", "max_results": 3 }
```

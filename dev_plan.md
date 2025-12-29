# Language-Learning Chatbot (Replit-First) — Architecture + Development Plan

## 1) Envisioned Architecture & Stack

### Goal

A text-only chatbot web app with:

- **Chat mode**: user chats with tutor bot
- **Language toggle**: switch display language; **entire chat history is translated**
- **Insights mode**: show **important words + sentence structures** from the conversation
- **Home page**: 5 topic starters

### Hosting/Platform

- **All-in-one on Replit (Free tier initially)**
    - One public URL (later optional custom domain)
    - One codebase
    - No Replit AI required (you use Copilot + Codex locally/in editor)

### Runtime Components (Monolith)

- **Backend**: Python API server (recommended: **FastAPI**; Flask also works)
- **Frontend**: Web UI served from the same app
    - Start **vanilla HTML/CSS/JS** for speed (upgrade to React later only if needed)
- **Database**: **SQLite** file in the Replit filesystem (MVP)
    - Tables for conversations/messages + caching translations/insights

### Request Flow

1. Browser loads `/` (static HTML/JS/CSS) served by the Python app
2. UI calls API endpoints:
    - `POST /api/chat` → bot response + persistence
    - `GET /api/conversations/{id}?display_lang=XX` → history in desired display language
    - `GET /api/insights/{id}?lang=XX` → vocab/structures (cached)
    - `GET /api/topics?lang=XX` → 5 topic starters
3. Backend stores canonical messages in SQLite; translations/insights cached for fast toggles.

### Data Model (MVP)

- `conversations(id, created_at)`
- `messages(id, conversation_id, role, lang, text, created_at)`
- `message_translations(message_id, lang, translated_text, created_at)` *(cache for language toggle)*
- `conversation_insights(conversation_id, lang, json, messages_hash, updated_at)` *(cache for insights)*

### Key Design Decisions

- **Canonical storage**: store original message text + language once; translate only for display.
- **Caching**: store per-message translations; store insights per conversation snapshot.
- **No auth initially**: use conversation links (e.g., `/?c=<conversation_id>`). Add login later if needed.

---

## 2) Detailed Development Plan (Issues; each < 0.5 day)

> Suggested sequence optimizes: fastest “working thing” → persistence → LLM → translation toggle → insights → polish.
> 

### Milestone A — Project Skeleton + Deployed “Hello”

**A1. Replit project bootstrap**

- Create Replit project (Python)
- Add FastAPI + uvicorn (or Flask)
- Add `/health` endpoint returning `{ "ok": true }`
- Add simple static page at `/` showing “Loaded” and calling `/health`

**Done when:** app loads in browser; `/health` returns ok.

---

### Milestone B — Chat UI + Stubbed Backend

**B1. Minimal chat UI (frontend)**

- Single-page UI:
    - message list (bubbles)
    - input + send button
    - basic layout (mobile-friendly)
- Local state only (no DB yet)

**Done when:** sending a message adds a user bubble.

**B2. Chat API (stub response)**

- `POST /api/chat` accepts:
    - `conversation_id` (optional)
    - `user_text`
    - `user_lang` (e.g., `en`)
- Returns:
    - `conversation_id` (generated if missing)
    - `assistant_text` (stubbed)
    - `assistant_lang`

**Done when:** UI calls backend and displays assistant reply.

---

### Milestone C — Persistence with SQLite

**C1. SQLite wiring**

- Add SQLite DB file + connection helper
- Create tables: `conversations`, `messages`
- Add basic migration/init function on startup

**Done when:** tables exist and app starts cleanly.

**C2. Persist chat messages**

- Update `POST /api/chat`:
    - create conversation if needed
    - insert user message
    - insert assistant message
- Add `GET /api/conversations/{id}` returning canonical history

**Done when:** refresh page can reload history from DB.

**C3. Conversation link handling**

- UI reads `?c=<id>` from URL
- If none, create new conversation via backend
- On new conversation, update URL to include `?c=<id>`

**Done when:** you can share a URL and see that conversation.

---

### Milestone D — LLM Integration (Text-only)

**D1. Add LLM client wrapper**

- Add env var secret: `LLM_API_KEY`
- Implement `llm_generate_reply(messages, target_lang, mode)` (initially mode = chat)
- Basic prompt: “You are a helpful language tutor…”

**Done when:** function returns plausible text.

**D2. Replace stubbed reply with LLM reply**

- In `POST /api/chat`:
    - fetch last N messages (e.g., 20)
    - call LLM
    - store assistant message

**Done when:** real tutor responses appear and persist.

---

### Milestone E — Language Toggle (Translate Full History)

**E1. Add translation cache table**

- Create `message_translations` table

**Done when:** table exists.

**E2. Conversation retrieval with `display_lang`**

- Implement `GET /api/conversations/{id}?display_lang=XX`
- For each message:
    - if `message.lang == display_lang`: `display_text = text`
    - else:
        - lookup cached translation
        - if missing → translate via LLM → store in cache
- Return messages with `display_text`

**Done when:** API returns history in requested language.

**E3. Frontend language toggle**

- Add language toggle button (e.g., EN/DE)
- On toggle: re-fetch conversation with `display_lang`
- Render `display_text` in bubbles

**Done when:** entire chat flips language instantly on subsequent toggles.

---

### Milestone F — Insights Mode (Words + Structures)

**F1. Insights cache table**

- Create `conversation_insights` table
- Add `messages_hash` (hash of last N messages or full convo) to invalidate cache

**Done when:** table exists.

**F2. Insights generation endpoint**

- `GET /api/insights/{id}?lang=XX`
- If cache hit (same messages_hash) → return cached JSON
- Else call LLM with instruction to output strict JSON:
    - `vocab`: term, meaning, example_from_chat
    - `structures`: pattern, explanation, example_from_chat

**Done when:** endpoint returns valid JSON consistently.

**F3. Insights UI tab**

- Add “Insights” tab/mode in UI
- Render vocab list + structures list
- Add simple UX:
    - search/filter vocab
    - expand to show examples

**Done when:** insights are readable and useful.

---

### Milestone G — Home Page + Topic Starters

**G1. Topics endpoint**

- `GET /api/topics?lang=XX`
- Start with curated list per language (no web trending yet)

**Done when:** endpoint returns 5 topics.

**G2. Home page UI**

- Home page with 5 chips/cards
- Clicking a topic:
    - starts/opens conversation
    - inserts topic text into chat input (or auto-sends)

**Done when:** topic → chat kickoff works in 1 click.

---

### Milestone H — Hardening + Beta Polish

**H1. Error handling + empty states**

- UI “loading…” and “error” states
- Backend returns consistent error JSON
- Handle missing conversation gracefully

**Done when:** app doesn’t look broken on failures.

**H2. Rate limiting + basic abuse prevention (light)**

- Simple per-IP request throttle in-memory (MVP)
- Basic request size limits

**Done when:** accidental spam doesn’t blow up.

**H3. Observability basics**

- Add structured logging for:
    - chat request start/end
    - translation cache hits/misses
    - insights cache hits/misses
- Add a `/debug/info` endpoint (optional, gated by env flag)

**Done when:** you can debug friend reports quickly.

**H4. Performance quick wins**

- Cache translations
- Cache insights
- Limit context window for LLM calls (last N messages)
- Add “regenerate response” button (optional)

**Done when:** it feels responsive for beta users.

---

## 3) Definition of Done (Beta-Ready)

- Chat works reliably (LLM-backed) and persists
- Shareable conversation link
- Language toggle translates entire history (with caching)
- Insights mode shows words + structures
- Home page has 5 starters
- Deployed on Replit free tier with a stable public URL

---

## 4) Later Upgrades (Not in MVP)

- Auth/accounts (email/OAuth)
- User preferences: learning language, correction strictness
- Streaming responses
- Managed Postgres migration
- True “trending” topics from external sources
- Mobile packaging (PWA → Capacitor)
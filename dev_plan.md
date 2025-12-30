# Language-Learning Chatbot (Replit-First) — Architecture + Development Plan (REVISED)

## 1) Envisioned Architecture & Stack

### Goal

A text-only chatbot web app with:

- **Landing page**: Language selection + 5 topic starters + free discussion button
- **Chat mode**: user chats with tutor bot
- **Language toggle**: switch display language; **entire chat history is translated**
- **Tutor mode**: Ask questions about words and sentences from the conversation
- **Insights**: show **important words + sentence structures** from the conversation

### Hosting/Platform

- **All-in-one on Replit (Free tier initially)**
    - One public URL (later optional custom domain)
    - One codebase
    - No Replit AI required (you use Copilot + Codex locally/in editor)

### Runtime Components (Monolith)

- **Backend**: Python API server (**FastAPI**)
- **Frontend**: Web UI served from the same app
    - **Vanilla HTML/CSS/JS** for speed (upgrade to React later only if needed)
- **Database**: **SQLite** file in the Replit filesystem (MVP)
    - Tables for conversations/messages + caching translations/insights

### Request Flow

1. Browser loads `/` (landing page) or `/chat` (chat page)
2. UI calls API endpoints:
    - `GET /api/topics?lang=XX` → topic starters
    - `POST /api/chat` → bot response + persistence
    - `GET /api/conversations/{id}?display_lang=XX` → history in desired display language
    - `POST /api/translate` → translate text
    - `GET /api/insights/{id}?lang=XX` → vocab/structures (cached)
3. Backend stores canonical messages in SQLite; translations/insights cached for fast toggles.

### Data Model (MVP)

- `conversations(id, primary_lang, secondary_lang, mode, created_at)`
- `messages(id, conversation_id, role, lang, text, created_at)`
- `message_translations(message_id, lang, translated_text, created_at)` *(cache for language toggle)*
- `conversation_insights(conversation_id, lang, json, messages_hash, updated_at)` *(cache for insights)*

### Key Design Decisions

- **Canonical storage**: store original message text + language once; translate only for display.
- **Caching**: store per-message translations; store insights per conversation snapshot.
- **No auth initially**: use conversation links (e.g., `/chat?c=<conversation_id>`). Add login later if needed.
- **Two-phase development**: Complete UI with stubs first, then implement real backends.

---

## 2) Detailed Development Plan — REVISED APPROACH

> **New Strategy:** Complete all UI components with stubbed backends first → then implement real backend functionality.
> This allows for rapid prototyping and easier UX iteration before committing to backend architecture.

---

## PHASE 1: UI Development with Stubbed Backends

### Milestone A — Project Skeleton + Deployed "Hello" ✅

**A1. Replit project bootstrap**

- Create Replit project (Python)
- Add FastAPI + uvicorn
- Add `/health` endpoint returning `{ "ok": true }`
- Add simple static page at `/` showing "Loaded" and calling `/health`

**Done when:** app loads in browser; `/health` returns ok.

**Status:** ✅ COMPLETE

---

### Milestone B — Landing/Welcome Page UI (Stubbed)

**B1. Landing page layout**

- Create welcome page at `/` route
- Header with app title and tagline
- Language selection section:
    - "Primary Language" dropdown (e.g., "I'm learning...")
    - "Secondary Language" dropdown (e.g., "I speak...")
    - List of common languages (EN, ES, FR, DE, IT, PT, ZH, JA, KO, AR, RU, HI)
- Topic starters section:
    - 5 clickable topic cards (e.g., Travel, Food, Hobbies, Work, Culture)
    - Each card shows title and brief description
- "Start Free Discussion" button (prominent CTA)
- All buttons navigate to `/chat` with appropriate query params

**Done when:** landing page displays with all UI elements; clicking any topic or button navigates to chat page with correct params.

**B2. Topics stub endpoint**

- `GET /api/topics?lang=XX` returns stubbed JSON:
    - Array of 5 topic objects: `{id, title, description}`
    - Hardcoded topics for now:
        - Travel: "Discuss travel experiences and dream destinations"
        - Food: "Talk about cuisine, recipes, and dining experiences"
        - Hobbies: "Share your interests and leisure activities"
        - Work: "Discuss career, workplace, and professional life"
        - Culture: "Explore traditions, arts, and cultural differences"

**Done when:** landing page fetches and displays topics from API.

---

### Milestone C — Basic Chat Page UI (Stubbed)

**C1. Chat page layout and routing**

- Create chat page at `/chat` route (separate from landing)
- Read URL params:
    - `?c=<id>` - conversation ID
    - `?topic=<id>` - selected topic
    - `?mode=tutor` - tutor mode flag
    - `?primary=<lang>` & `?secondary=<lang>` - language preferences
- Header with:
    - App title/logo (links back to home)
    - Language toggle button (shows current display language)
    - "Tutor Mode" button
    - Back to home button (icon)
- Message list area:
    - User bubbles (right side, colored)
    - Assistant bubbles (left side, white/light)
    - Message timestamps
    - Auto-scroll to newest message
- Input area:
    - Text input field (full width)
    - Send button (icon)
- Welcome message on empty chat
- If topic was selected, auto-send topic as first message

**Done when:** chat page displays with all UI controls; can type and send messages.

**C2. Chat stub endpoint**

- `POST /api/chat` accepts:
    - `conversation_id` (optional, generate if missing)
    - `user_text`
    - `user_lang`
    - `display_lang` (optional)
    - `mode` ("chat" or "tutor", default "chat")
- Returns:
    - `conversation_id` (UUID)
    - `assistant_text` (stubbed response based on mode)
    - `assistant_lang`
- Stub logic:
    - Chat mode: "That's interesting! Tell me more about [topic]."
    - Tutor mode: "Great question! Let me explain [concept]."
    - Add 1-2 second delay to simulate LLM

**Done when:** UI calls API and displays stubbed assistant responses; conversation ID is generated and stored.

---

### Milestone D — Language Toggle UI (Stubbed)

**D1. Language toggle button implementation**

- Toggle button in chat header:
    - Shows current display language (e.g., "EN" or "ES")
    - Icon or text button that's clearly clickable
    - Tooltip explaining functionality
- Clicking toggle:
    - Cycles between primary and secondary language
    - Shows loading indicator
    - Re-fetches/re-renders all messages
    - Updates URL param `?display=XX`
    - Maintains scroll position after update

**Done when:** clicking toggle button switches display language indicator and re-renders messages.

**D2. Translation stub endpoint**

- `POST /api/translate` accepts:
    - `text` (string or array of strings)
    - `source_lang`
    - `target_lang`
- Returns:
    - `translated_text` (string or array)
- Stub logic:
    - Simply returns: "[Translated to {target_lang}] {original_text}"
    - Add small delay (200-500ms) to simulate API call

**Done when:** language toggle calls API and displays "translated" messages with prefix.

**D3. Conversation history stub endpoint**

- `GET /api/conversations/{id}?display_lang=XX` returns:
    - `conversation_id`
    - `primary_lang`
    - `secondary_lang`
    - `mode`
    - `messages`: array of message objects with:
        - `id`
        - `role` (user/assistant)
        - `text` (in display_lang)
        - `original_lang`
        - `timestamp`
- For now, use localStorage to store/retrieve conversation
- Apply stub translation to each message if display_lang differs

**Done when:** page reload fetches conversation and displays with correct language.

---

### Milestone E — Tutor Mode UI (Stubbed)

**E1. Tutor mode button and flow**

- "Tutor Mode" button in chat header:
    - Icon + label (e.g., "Ask Tutor 💡")
    - When clicked:
        - Option A: Opens modal/sidebar with insights
        - Option B (simpler): Starts new conversation in tutor mode
    - For MVP: implement Option B
- Tutor mode conversation:
    - Clears current messages (or navigates to `/chat?mode=tutor&prev=<id>`)
    - Shows different welcome message: "I'm here to answer your questions about words, grammar, and phrases from our conversation. What would you like to know?"
    - Different assistant behavior (questioning/explanatory)
    - Button to return to regular chat mode

**Done when:** clicking tutor mode button starts fresh conversation with different context.

**E2. Insights preview (optional for Phase 1)**

- Add "View Insights" button next to tutor mode
- Shows modal or sidebar with:
    - "Key Vocabulary" section (empty or stubbed)
    - "Sentence Patterns" section (empty or stubbed)
    - Message: "Continue chatting to see insights!"
- For now, just UI placeholder

**Done when:** insights modal/sidebar can be opened and closed.

---

### Milestone F — Client-Side State Management

**F1. Navigation and routing**

- Implement proper client-side routing:
    - `/` → Landing page
    - `/chat` → Chat page (with query params)
- URL parameter handling:
    - Store/read from URL: conversation ID, mode, topic, languages
    - Update URL without reload when state changes
- Browser back/forward button handling
- Sharable URLs work correctly

**Done when:** can navigate between pages; URLs are bookmarkable and shareable.

**F2. Local storage persistence**

- Store in localStorage:
    - Current conversation messages (temp, until backend persists)
    - Language preferences (primary, secondary)
    - Last conversation ID
- On page reload:
    - Restore language preferences
    - Attempt to load conversation from localStorage
- Clear localStorage when starting new conversation

**Done when:** page refresh preserves conversation state and preferences.

---

### Milestone G — UI Polish & Responsive Design

**G1. Responsive design for all pages**

- Landing page responsive:
    - Topic cards stack on mobile
    - Dropdowns full-width on mobile
    - Buttons properly sized for touch
- Chat page responsive:
    - Full-screen on mobile
    - Header collapses to icons on small screens
    - Message bubbles max 85% width on mobile
    - Input area always visible (sticky)
- Test on: desktop, tablet (landscape/portrait), mobile (various sizes)

**Done when:** all pages work perfectly on all device sizes.

**G2. Loading and error states**

- Loading indicators:
    - Page load skeleton/spinner
    - Message sending (typing indicator)
    - Language toggle (loading overlay)
    - API calls (loading states on buttons)
- Error states:
    - Failed API calls (show retry button)
    - Network offline (show offline banner)
    - Invalid conversation ID (redirect to home)
- Empty states:
    - No topics loaded (show error message)
    - No messages yet (show welcome message)

**Done when:** all possible states are handled with clear UI feedback.

**G3. Animations and micro-interactions**

- Page transitions (smooth fade or slide)
- Message animations (slide in from right/left)
- Button hover/active states (scale, color)
- Language toggle animation (flip or rotate)
- Typing indicator animation (bouncing dots)
- Loading spinners (smooth rotation)
- Focus states for accessibility

**Done when:** UI feels polished, smooth, and professional.

---

## PHASE 2: Backend Implementation (Replace Stubs)

### Milestone H — Database Setup & Persistence

**H1. SQLite database wiring**

- Add `aiosqlite` or `sqlite3` dependency
- Create `db.py` module with connection helper
- Create tables:
    - `conversations(id, primary_lang, secondary_lang, mode, created_at)`
    - `messages(id, conversation_id, role, lang, text, created_at)`
    - `message_translations(message_id, lang, translated_text, created_at)`
- Add init function to run on app startup
- Add migration/schema versioning (simple)

**Done when:** tables exist; app starts cleanly with DB initialized.

**H2. Persist conversations and messages**

- Update `POST /api/chat`:
    - Create conversation record if new
    - Insert user message into DB
    - Insert assistant message into DB (still stubbed response)
    - Return conversation_id
- Add `GET /api/conversations/{id}`:
    - Query messages from DB
    - Return messages in original language
    - Include conversation metadata

**Done when:** messages persist in DB; page refresh loads from DB instead of localStorage.

**H3. URL-based conversation loading**

- Update chat page to fetch conversation from DB using `?c=<id>`
- Display full conversation history on load
- Handle edge cases:
    - Conversation not found → redirect to home with error
    - Empty conversation → show welcome message
- Remove localStorage persistence (now using DB)

**Done when:** shareable conversation URLs work; conversations persist across sessions.

---

### Milestone I — LLM Integration

**I1. LLM client wrapper setup**

- Add environment variable: `LLM_API_KEY`
- Add `openai` or `anthropic` library (or similar)
- Create `llm.py` module with:
    - `generate_reply(messages, target_lang, mode, system_prompt)` function
    - Error handling and retry logic
    - Token/cost tracking (optional)
- Define system prompts:
    - **Chat mode**: "You are a helpful language tutor. Have natural conversations and gently correct mistakes. Respond in {target_lang}."
    - **Tutor mode**: "You are a language tutor answering questions about vocabulary, grammar, and language usage. Be clear and educational. Respond in {target_lang}."

**Done when:** LLM function returns real responses; can be called with different prompts.

**I2. Replace stubbed chat responses with LLM**

- Update `POST /api/chat`:
    - Fetch last N messages from DB (e.g., 20)
    - Format messages for LLM context
    - Call `generate_reply()` with appropriate mode
    - Store LLM response in DB
    - Return response to client
- Handle LLM errors:
    - Timeouts → return friendly error
    - Rate limits → queue or backoff
    - Invalid responses → retry or fallback

**Done when:** real tutor responses appear in chat; conversations feel natural.

---

### Milestone J — Translation Implementation

**J1. Translation function with caching**

- Create `translation.py` module
- Implement `translate_text(text, source_lang, target_lang)`:
    - Check `message_translations` table first (cache)
    - If cache miss: call LLM for translation
    - Store result in cache
    - Return translated text
- Batch translation support for efficiency
- Use simple LLM prompt: "Translate this from {source} to {target}, preserve tone and context: {text}"

**Done when:** translation function works with caching.

**J2. Replace stubbed translation endpoint**

- Update `POST /api/translate`:
    - Call `translate_text()` instead of stub
    - Support single text or array of texts
    - Return translations
- Add rate limiting to prevent abuse

**Done when:** language toggle shows real translations.

**J3. Conversation translation on retrieval**

- Update `GET /api/conversations/{id}?display_lang=XX`:
    - For each message:
        - If `message.lang == display_lang`: return original text
        - Else: get/generate translation from cache
    - Batch translate all messages if needed
    - Optimize query to join with translations table
- Return messages with `text` in requested display_lang

**Done when:** full conversation instantly translates on language toggle (with cache).

---

### Milestone K — Tutor Mode & Insights Enhancement

**K1. Insights generation function**

- Create `insights.py` module
- Create `conversation_insights` table:
    - `conversation_id, lang, vocab_json, patterns_json, messages_hash, updated_at`
- Implement `generate_insights(conversation_id, display_lang)`:
    - Hash recent messages to check if cache valid
    - If cache hit: return cached insights
    - If cache miss:
        - Fetch conversation messages
        - Call LLM with structured prompt to extract:
            - **Vocabulary**: {word, definition, example_from_chat, usage_notes}
            - **Patterns**: {pattern, explanation, example_from_chat}
        - Parse LLM response (JSON format)
        - Cache in DB
        - Return insights

**Done when:** insights generation works and returns structured JSON.

**K2. Insights endpoint**

- Implement `GET /api/insights/{id}?lang=XX`:
    - Call `generate_insights()`
    - Return JSON with vocab and patterns arrays
    - Handle errors gracefully

**Done when:** endpoint returns real insights data.

**K3. Enhanced tutor mode UI with insights**

- Update "Tutor Mode" button to show modal/sidebar:
    - Fetch insights from `/api/insights/{id}`
    - Display vocabulary list:
        - Each word expandable to show definition and example
        - Click word to ask question about it in chat
    - Display sentence patterns:
        - Each pattern expandable
        - Examples highlighted from conversation
- Keep option to start tutor mode conversation
- Add loading states for insights generation

**Done when:** tutor mode shows real insights; users can explore vocabulary and patterns.

---

### Milestone L — Polish & Production Readiness

**L1. Real topics implementation**

- Replace stubbed topics with curated real topics:
    - Create `topics.json` or `topics` DB table
    - Include 15-20 topics per language category
    - Add variety: cultural, practical, fun topics
- Update `GET /api/topics?lang=XX` to return real topics
- Optionally: randomize which 5 are shown

**Done when:** topics are meaningful, varied, and language-appropriate.

**L2. Error handling & logging**

- Add comprehensive error handling:
    - All endpoints return consistent error JSON format
    - User-friendly error messages
    - Log errors with context for debugging
- Add structured logging:
    - Request IDs for tracing
    - Log key events: chat requests, LLM calls, cache hits/misses
    - Performance metrics (response times)
- Add `/api/health` endpoint with DB and LLM status checks

**Done when:** errors are handled gracefully; logs are useful for debugging.

**L3. Performance optimization**

- Implement caching strategies:
    - Cache translations aggressively
    - Cache insights until conversation changes
    - Use DB indexes for fast queries
- Optimize LLM calls:
    - Limit context window (last 20 messages)
    - Batch translations when possible
    - Stream responses if library supports (future)
- Add request rate limiting:
    - Per-IP limits (simple in-memory)
    - Prevent spam/abuse

**Done when:** app feels fast; backend handles load efficiently.

**L4. Testing & bug fixes**

- Test all user flows:
    - New conversation from landing page
    - Language toggle in active conversation
    - Tutor mode activation and usage
    - Conversation sharing via URL
    - Page refresh and state persistence
- Test edge cases:
    - Invalid conversation IDs
    - Network failures
    - Empty conversations
    - Very long messages
- Cross-browser testing (Chrome, Firefox, Safari, Edge)
- Mobile device testing (iOS Safari, Android Chrome)
- Fix all bugs found

**Done when:** app works reliably across browsers and devices; no critical bugs.

---

## 3) Definition of Done (Beta-Ready)

- ✅ Landing page with language selection and topic starters
- ✅ Chat works reliably (LLM-backed) and persists
- ✅ Shareable conversation links work
- ✅ Language toggle translates entire history (with caching)
- ✅ Tutor mode with insights shows words + patterns
- ✅ Responsive design works on mobile, tablet, desktop
- ✅ Error handling is comprehensive
- ✅ Deployed on Replit free tier with stable public URL
- ✅ All UI flows are smooth and polished

---

## 4) Later Upgrades (Not in MVP)

- Auth/accounts (email/OAuth)
- User profiles with learning preferences
- Correction strictness settings
- Streaming LLM responses (real-time typing)
- Voice input/output (text-to-speech, speech-to-text)
- Managed Postgres migration (if scale requires)
- True "trending" topics from external sources
- Spaced repetition for vocabulary practice
- Progress tracking and analytics
- Mobile app packaging (PWA → Capacitor/React Native)
- Multi-user conversations (study groups)
- Export conversation as PDF/text

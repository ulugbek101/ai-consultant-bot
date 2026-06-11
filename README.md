# Прокар Эксперт Аудит — Telegram Bot

AI-powered consulting bot for **Prokar Expert Audit** — an auditing and accounting firm based in Tashkent, Uzbekistan. The bot acts as a 24/7 virtual consultant, answers business questions using an LLM, captures client leads, and provides an admin panel for the company manager.

---

## Features

### For clients (regular users)
- **7 service categories** with subcategories — user picks a category, then a subcategory, then types a question; the question is sent to the AI with full context (`Category → Subcategory → Question`)
- **Free-form AI chat** — users can also just type any question without selecting a category
- **Conversation memory** — last 12 messages are kept as context so the AI understands follow-up questions
- **Contact form** — multi-step FSM form (name → phone → email → company → question); supports Telegram's native "Share phone number" button; validates Uzbekistan phone format (`+998XXXXXXXXX`)
- **Markdown rendering** — AI responses with `**bold**`, `*italic*`, `` `code` ``, `# headers`, `- lists` are converted to Telegram HTML before delivery
- `/start` and `/help` commands

### For the admin
All admin commands are only visible and accessible to the user whose Telegram ID is set as `ADMIN_CHAT_IDS`. Regular users cannot see or trigger them.

| Command | Description |
|---|---|
| `/admin` | Show admin panel help |
| `/users [page]` | Paginated list of all registered users (10 per page), sorted by last activity |
| `/user <id>` | Full profile of a user + sends an HTML file with up to 200 messages of chat history styled like a Telegram conversation |
| `/stats` | Total users, new today, total/today/weekly message counts, top-5 most active users |
| `/topics` | Topic distribution for the last 30 days (tax, accounting, legal, etc.) |

**Topic classification** — every user message is automatically classified into one of 7 topics at save time using keyword matching. No external API calls needed.

**Chat history export** — `/user <id>` sends a self-contained `.html` file that renders as a Telegram-style chat (blue header, outgoing/incoming bubbles, date separators, timestamps). Opens in any browser, no dependencies.

---

## Tech stack

| Layer | Technology |
|---|---|
| Bot framework | [aiogram 3](https://docs.aiogram.dev/) |
| AI | OpenAI API (`gpt-4o-mini` by default) |
| Database | MySQL via `PyMySQL` |
| Python | 3.12 |
| Config | `environs` + `.env` file |

---

## Project structure

```
.
├── app.py                    # Entry point: startup, polling, command menu registration
├── config.py                 # Env var loading
├── loader.py                 # Bot, Dispatcher, DB singletons
├── router.py                 # Single shared aiogram Router
│
├── handlers/
│   ├── start.py              # /start, /help, end_chat
│   ├── ai_chat.py            # Service buttons, subcategory flow, free-text AI chat
│   ├── contact.py            # Multi-step contact form (FSM)
│   └── admin.py              # All admin commands + HTML export builder
│
├── keyboards/
│   ├── inline/__init__.py    # All InlineKeyboardMarkup builders
│   └── reply/__init__.py     # ReplyKeyboardMarkup (phone sharing button)
│
├── states/__init__.py        # FSM state groups (ContactStates, AIChatStates)
│
├── utils/
│   ├── db_api/db.py          # Database class — all SQL queries
│   ├── gemini_api.py         # OpenAI client wrapper + system prompt
│   └── md_to_html.py         # Markdown → Telegram HTML converter
│
├── guide.html                # End-user guide (for clients and admin)
└── requirements.txt
```

---

## Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd ai-consultant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create `.env` file

```env
TOKEN=<your Telegram bot token>
ADMIN_CHAT_IDS=<your Telegram user ID>
OPENAI_API_KEY=<your OpenAI API key>

DB_NAME=prokar_bot
DB_USER=root
DB_PASSWORD=<password>
DB_HOST=127.0.0.1
DB_PORT=3306
```

> **ADMIN_CHAT_IDS** — the Telegram numeric ID of the manager. Get it from [@userinfobot](https://t.me/userinfobot). This user will see admin commands in the "/" menu and can use all `/admin`, `/users`, `/user`, `/stats`, `/topics` commands.

### 3. Create MySQL database

```sql
CREATE DATABASE prokar_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Tables are created automatically on first startup via `db.create_tables()`. The subcategory seed data (26 subcategories across 7 categories) is also inserted automatically on first startup via `db.seed_subcategories()` — it checks if the table is empty before inserting, so restarts are safe.

### 4. Run

```bash
python app.py
```

---

## Database schema

### `users`
| Column | Type | Description |
|---|---|---|
| `id` | INT PK | Auto-increment |
| `telegram_id` | BIGINT UNIQUE | Telegram user ID |
| `first_name`, `last_name`, `fullname` | VARCHAR | From Telegram profile |
| `username` | VARCHAR | @handle |
| `language_code` | VARCHAR | e.g. `ru`, `uz` |
| `is_premium` | TINYINT | Telegram Premium flag |
| `phone` | VARCHAR | Filled via contact form |
| `email` | VARCHAR | Filled via contact form |
| `company_name` | VARCHAR | Filled via contact form |
| `business_type` | VARCHAR | Reserved |
| `city` | VARCHAR | Filled via contact form |
| `notes` | TEXT | User's question from contact form |
| `message_count` | INT | Total questions sent |
| `last_active_at` | TIMESTAMP | Updated on every message |
| `created_at` | TIMESTAMP | First /start |

### `messages`
| Column | Type | Description |
|---|---|---|
| `id` | INT PK | Auto-increment |
| `telegram_id` | BIGINT | Foreign key → users |
| `role` | VARCHAR(15) | `user` or `assistant` |
| `content` | TEXT | Message text |
| `topic` | VARCHAR(50) | Auto-classified: `tax`, `accounting`, `legal`, `audit`, `credit`, `finance`, `hr`, `other` |
| `created_at` | TIMESTAMP | — |

### `subcategories`
| Column | Type | Description |
|---|---|---|
| `id` | INT PK | Auto-increment |
| `category_key` | VARCHAR(50) | e.g. `svc_tax`, `svc_accounting` |
| `label` | VARCHAR(200) | Display text on the button |
| `sort_order` | INT | Controls button order |
| `is_active` | TINYINT | Set to `0` to hide without deleting |
| `created_at` | TIMESTAMP | — |

To add a new subcategory at runtime:
```sql
INSERT INTO subcategories (category_key, label, sort_order)
VALUES ('svc_tax', 'Новая подкатегория', 5);
```

To disable one:
```sql
UPDATE subcategories SET is_active = 0 WHERE id = 12;
```

---

## Service categories and subcategories

| Key | Button label | Subcategories |
|---|---|---|
| `svc_accounting` | 📒 Помощь с бухгалтерией | Учет по НСБУ, Учет по МСФО, Восстановление учета, Импорт/экспорт |
| `svc_tax` | 📊 Налоговое консультирование | Выбор системы налогообложения, Отчетность, Требования ГНИ, Налоговый аудит |
| `svc_legal` | ⚖️ Юридическая консультация | Регистрация ООО/СП/ЯТТ, Экспертиза договоров, Работа с должниками, Трудовое право |
| `svc_audit` | 🔍 Аудит | Обязательный/инициативный аудит, IT Park, Крупные сделки, МСФО |
| `svc_credit` | 💳 Кредиты и инвестиции | Получение кредитов, Бизнес-планы и ТЭО |
| `svc_finance` | 💼 Финансовый консалтинг | Корпоративное управление, Учредители/инвесторы, Госзакупки, ФХД |
| `svc_hr` | 👥 Кадровый учёт | Кадровый учет, Трудовое законодательство |

---

## AI integration

File: [`utils/gemini_api.py`](utils/gemini_api.py)

- Client: `openai.OpenAI` (sync, wrapped in `asyncio.to_thread`)
- Model: `gpt-4o-mini` — change on line 43 to `gpt-4o` for higher quality
- Context window: last **12 messages** per user sent to the API (configurable in `ai_chat.py:42`)
- System prompt enforces:
  - Only answers questions relevant to the company's 7 service areas
  - Only uses **Uzbekistan law** (Налоговый кодекс РУз, ГК РУз, ТК РУз, etc.)
  - Refuses off-topic questions with a polite redirect
  - Responds in Russian or Uzbek depending on the user's language
  - Never uses Chinese, Japanese, Korean or other non-Cyrillic/Latin characters

### Question context format
When a user selects a subcategory, the question sent to the AI is:
```
Налоговое консультирование → Подготовка налоговой отчетности → Как заполнить форму НДС?
```
This ensures the AI has full context even if the question itself is brief.

---

## Markdown → HTML conversion

File: [`utils/md_to_html.py`](utils/md_to_html.py)

LLM responses use standard Markdown. Since the bot uses `ParseMode.HTML`, all AI replies are passed through `md_to_html()` before sending. Supported conversions:

| Markdown | Telegram HTML |
|---|---|
| `**bold**` | `<b>bold</b>` |
| `*italic*` or `_italic_` | `<i>italic</i>` |
| `` `code` `` | `<code>code</code>` |
| ` ```block``` ` | `<pre>block</pre>` |
| `~~strike~~` | `<s>strike</s>` |
| `# Heading` | `<b>Heading</b>` |
| `- item` | `• item` |

HTML entities (`&`, `<`, `>`) in the source text are escaped before pattern matching to prevent injection.

---

## Contact form flow (FSM)

State machine in [`states/__init__.py`](states/__init__.py) — `ContactStates`:

```
callback: contact_consultant
    → waiting_for_name      (text)
    → waiting_for_phone     (contact OR text, validated as +998XXXXXXXXX)
    → waiting_for_email     (text, optional)
    → waiting_for_company   (text, optional)
    → waiting_for_question  (text)
        → saves to DB, sends notification to ADMIN_CHAT_IDS
```

At the phone step, a `ReplyKeyboardMarkup` is shown with a native "Share phone number" button. On success the reply keyboard is removed and inline keyboards resume.

---

## Admin HTML chat export

When the admin runs `/user <id>`, the bot:
1. Sends the user's profile as a Telegram message (escaped with `html.escape()`)
2. Generates a self-contained HTML file (`chat_<id>_<date>.html`) and sends it as a document

The HTML file mimics Telegram's visual design:
- Sticky blue header with user's initial avatar
- Profile card (contact details in a grid)
- Chat bubbles: outgoing (green `#EFFFDE`) on the right, incoming (white) on the left
- CSS bubble tails, date separators, timestamps
- Bot responses rendered with full HTML formatting (bold, code blocks, etc.)

---

## Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `TOKEN` | ✅ | Telegram bot token from @BotFather |
| `ADMIN_CHAT_IDS` | ✅ | Telegram ID of the admin user |
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `DB_NAME` | ✅ | MySQL database name |
| `DB_USER` | ✅ | MySQL user |
| `DB_PASSWORD` | ✅ | MySQL password |
| `DB_HOST` | ✅ | MySQL host (e.g. `127.0.0.1`) |
| `DB_PORT` | ✅ | MySQL port (e.g. `3306`) |

---

## End-user guide

A detailed HTML guide for both clients and the admin manager is available at [`guide.html`](guide.html). Open it in any browser. It covers every feature with visual Telegram mockups, step-by-step instructions, a command reference table, and FAQ.

---

## Developer notes

- **Adding a subcategory** — insert a row into `subcategories` table; no code change needed
- **Disabling a subcategory** — set `is_active = 0`; it disappears from buttons immediately
- **Changing the AI model** — edit `model=` in `utils/gemini_api.py`
- **Changing history window** — edit `limit=12` in `handlers/ai_chat.py`
- **Adding a new main category** — add to `services_keyboard()`, `_CATEGORY_LABELS`, `_SERVICE_PROMPTS` in `ai_chat.py`, and insert subcategories into the DB
- **All user data is HTML-escaped** before being inserted into Telegram messages to prevent entity parse errors

---

## Company

**Прокар Эксперт Аудит**
г. Ташкент, Яккасарайский р-н, ул. Кичик Бешегов 70, 2
📞 +998 90 919 20 35 / +998 90 188 69 12
🌐 [prokar.uz](https://www.prokar.uz) · ISO 9001

**Developer:** Улугбек Умаралиев · [@thedevu101](https://t.me/thedevu101) · +998 99 693 73 08

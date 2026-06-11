import html as html_lib
import math
from datetime import datetime

from aiogram import types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from config import ADMIN_CHAT_IDS
from loader import db
from router import router
from utils.md_to_html import md_to_html

PER_PAGE = 10

_TOPIC_LABELS = {
    "tax":         "🏦 Налоги",
    "accounting":  "📚 Бухучёт",
    "legal":       "⚖️ Юридические",
    "procurement": "🏛️ Госзакупки",
    "ecology":     "🌿 Экология",
    "business":    "💼 Бизнес",
    "other":       "❓ Прочее",
}


def _is_admin(message: types.Message) -> bool:
    return message.from_user.id in ADMIN_CHAT_IDS


def _ago(dt: datetime | None) -> str:
    if dt is None:
        return "никогда"
    diff = datetime.now() - dt
    if diff.days > 30:
        return dt.strftime("%d.%m.%Y")
    if diff.days > 0:
        return f"{diff.days} дн. назад"
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} ч. назад"
    mins = diff.seconds // 60
    return f"{mins} мин. назад" if mins > 0 else "только что"


# ── /admin ────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: types.Message) -> None:
    if not _is_admin(message):
        return
    await message.answer(
        "🛠 <b>Панель администратора</b>\n\n"
        "/users — список пользователей\n"
        "/user &lt;id&gt; — профиль и переписка пользователя\n"
        "/stats — общая статистика\n"
        "/topics — темы запросов за 30 дней"
    )


# ── /users ────────────────────────────────────────────────────────────────────

@router.message(Command("users"))
async def cmd_users(message: types.Message) -> None:
    if not _is_admin(message):
        return
    args = message.text.split()
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    await _send_users_page(message, page)


async def _send_users_page(message: types.Message, page: int) -> None:
    total = await db.get_users_count()
    if not total:
        await message.answer("Пользователей пока нет.")
        return

    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = max(1, min(page, total_pages))
    users = await db.get_users_page(page, PER_PAGE)

    lines = [f"👥 <b>Пользователи</b> — стр. {page}/{total_pages} (всего {total})\n"]
    for i, u in enumerate(users, start=(page - 1) * PER_PAGE + 1):
        name = html_lib.escape(u["fullname"] or "—")
        uname = f" @{html_lib.escape(u['username'])}" if u["username"] else ""
        lines.append(
            f"{i}. <b>{name}</b>{uname}\n"
            f"   💬 {u['message_count'] or 0} сообщ. · {_ago(u['last_active_at'])}\n"
            f"   🆔 <code>{u['telegram_id']}</code>"
        )

    nav = []
    if page > 1:
        nav.append(f"/users {page - 1}  ◀")
    if page < total_pages:
        nav.append(f"▶  /users {page + 1}")
    if nav:
        lines.append("\n" + "     ".join(nav))

    await message.answer("\n".join(lines))


_HTML_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #dae8f5; font-size: 14px; color: #222;
}
.tg-header {
  position: sticky; top: 0; z-index: 100;
  background: #2aabee; color: #fff;
  padding: 10px 16px; display: flex; align-items: center; gap: 12px;
  box-shadow: 0 2px 6px rgba(0,0,0,.25);
}
.tg-header .av {
  width: 40px; height: 40px; border-radius: 50%;
  background: #1a8cc7; display: flex; align-items: center;
  justify-content: center; font-size: 18px; font-weight: 700; flex-shrink: 0;
}
.tg-header .hname { font-weight: 600; font-size: 16px; }
.tg-header .hsub  { font-size: 12px; opacity: .85; margin-top: 1px; }
.profile-card {
  background: #fff; max-width: 860px; margin: 16px auto;
  border-radius: 12px; padding: 16px 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.1);
}
.profile-card .pc-title { font-size: 13px; color: #2aabee; font-weight: 600; margin-bottom: 10px; }
.profile-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(170px,1fr)); gap: 8px; }
.pf .lbl { font-size: 11px; color: #999; text-transform: uppercase; letter-spacing:.4px; }
.pf .val { font-size: 13px; font-weight: 500; margin-top: 2px; word-break: break-all; }
.messages { max-width: 860px; margin: 0 auto; padding: 8px 0 24px; }
.date-sep { display: flex; justify-content: center; margin: 14px 0 6px; }
.date-sep span {
  background: rgba(0,0,0,.28); color: #fff;
  font-size: 12px; padding: 4px 14px; border-radius: 12px;
}
.msg-row { display: flex; align-items: flex-end; gap: 6px; margin: 2px 16px; }
.msg-row.out { justify-content: flex-end; }
.msg-row.inc { justify-content: flex-start; }
.bot-av {
  width: 30px; height: 30px; border-radius: 50%; background: #2aabee;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; flex-shrink: 0;
}
.msg-row.inc.no-av .bot-av { visibility: hidden; }
.bubble {
  max-width: 68%; padding: 7px 11px 20px;
  border-radius: 12px; position: relative;
  word-break: break-word; line-height: 1.48;
  box-shadow: 0 1px 2px rgba(0,0,0,.12);
}
.out .bubble {
  background: #efffde; border-bottom-right-radius: 3px;
}
.inc .bubble {
  background: #fff; border-bottom-left-radius: 3px;
}
.out .bubble::after {
  content:''; position:absolute; bottom:0; right:-7px;
  border:7px solid transparent; border-bottom-color:#efffde;
  border-right:0; border-top:0;
}
.inc .bubble::after {
  content:''; position:absolute; bottom:0; left:-7px;
  border:7px solid transparent; border-bottom-color:#fff;
  border-left:0; border-top:0;
}
.bubble .text { white-space: pre-wrap; font-size: 14px; }
.bubble .text b  { font-weight: 600; }
.bubble .text i  { font-style: italic; }
.bubble .text s  { text-decoration: line-through; }
.bubble .text code {
  background: rgba(0,0,0,.07); padding: 1px 4px;
  border-radius: 3px; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12.5px;
}
.bubble .text pre {
  background: rgba(0,0,0,.06); padding: 8px; border-radius: 6px;
  font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px;
  overflow-x: auto; margin: 4px 0; white-space: pre;
}
.bubble .ts {
  position: absolute; bottom: 4px; right: 8px;
  font-size: 10.5px; color: #7c8a93; white-space: nowrap;
}
.out .bubble .ts { color: #6a9e73; }
.export-note { text-align: center; padding: 20px; font-size: 11px; color: rgba(0,0,0,.35); }
"""


def _build_history_html(user: dict, history: list) -> str:
    def esc(v): return html_lib.escape(str(v)) if v else "—"

    name    = esc(user.get("fullname"))
    initial = (user.get("fullname") or "?")[0].upper()
    uname   = f"@{esc(user['username'])}" if user.get("username") else ""
    created = user["created_at"].strftime("%d.%m.%Y") if user.get("created_at") else "—"
    export_dt = datetime.now().strftime("%d.%m.%Y %H:%M")

    profile_fields = [
        ("Telegram ID", str(user["telegram_id"]) + (f" · {uname}" if uname else "")),
        ("Телефон",     user.get("phone")),
        ("Email",       user.get("email")),
        ("Компания",    user.get("company_name")),
        ("Город",       user.get("city")),
        ("Зарегистрирован", created),
        ("Сообщений",   str(user.get("message_count") or 0)),
        ("Последний",   _ago(user.get("last_active_at"))),
    ]
    pf_html = "".join(
        f'<div class="pf"><div class="lbl">{esc(lbl)}</div>'
        f'<div class="val">{esc(val)}</div></div>'
        for lbl, val in profile_fields if val
    )
    if user.get("notes"):
        pf_html += (
            f'<div class="pf" style="grid-column:1/-1">'
            f'<div class="lbl">Вопрос</div>'
            f'<div class="val"><i>{esc(user["notes"])}</i></div></div>'
        )

    msgs_html = ""
    prev_date = None
    prev_role = None

    for row in history:
        is_out = row["role"] == "user"
        dt_obj = row.get("created_at")
        ts_str = dt_obj.strftime("%H:%M") if dt_obj else ""
        date_str = dt_obj.strftime("%d %B %Y") if dt_obj else ""

        if date_str and date_str != prev_date:
            msgs_html += f'<div class="date-sep"><span>{html_lib.escape(date_str)}</span></div>\n'
            prev_date = date_str

        same_sender = (row["role"] == prev_role)
        av_class = "no-av" if same_sender else ""
        prev_role = row["role"]

        content = esc(row["content"]) if is_out else md_to_html(row["content"])

        if is_out:
            msgs_html += (
                f'<div class="msg-row out">'
                f'<div class="bubble"><div class="text">{content}</div>'
                f'<div class="ts">{ts_str}</div></div></div>\n'
            )
        else:
            msgs_html += (
                f'<div class="msg-row inc {av_class}">'
                f'<div class="bot-av">🤖</div>'
                f'<div class="bubble"><div class="text">{content}</div>'
                f'<div class="ts">{ts_str}</div></div></div>\n'
            )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>История чата — {name}</title>
  <style>{_HTML_CSS}</style>
</head>
<body>
  <div class="tg-header">
    <div class="av">{html_lib.escape(initial)}</div>
    <div>
      <div class="hname">{name}</div>
      <div class="hsub">{uname or ('ID ' + str(user['telegram_id']))}</div>
    </div>
  </div>

  <div class="profile-card">
    <div class="pc-title">Профиль пользователя</div>
    <div class="profile-grid">{pf_html}</div>
  </div>

  <div class="messages">{msgs_html}</div>

  <div class="export-note">Прокар Эксперт Аудит · prokar.uz · Экспорт {export_dt}</div>
</body>
</html>"""


# ── /user <id> ────────────────────────────────────────────────────────────────

@router.message(Command("user"))
async def cmd_user(message: types.Message) -> None:
    if not _is_admin(message):
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].lstrip("-").isdigit():
        await message.answer("Использование: /user &lt;telegram_id&gt;")
        return

    tid = int(args[1])
    user = await db.get_user(tid)
    if not user:
        await message.answer("Пользователь не найден.")
        return

    def e(v): return html_lib.escape(str(v)) if v else "—"
    uname = f" · @{e(user['username'])}" if user["username"] else ""
    created = user["created_at"].strftime("%d.%m.%Y") if user.get("created_at") else "—"
    profile = (
        f"👤 <b>{e(user['fullname'])}</b>\n"
        f"🆔 <code>{tid}</code>{uname}\n"
        f"📱 {e(user['phone'])}\n"
        f"📧 {e(user['email'])}\n"
        f"🏢 {e(user['company_name'])}\n"
        f"🏙 {e(user['city'])}\n"
        f"💬 Сообщений: <b>{user['message_count'] or 0}</b>\n"
        f"🕐 Последний: {_ago(user['last_active_at'])}\n"
        f"📅 Зарегистрирован: {created}"
    )
    if user.get("notes"):
        profile += f"\n📝 <i>{e(user['notes'])}</i>"

    await message.answer(profile)

    history = await db.get_full_history(tid, limit=200)
    if not history:
        await message.answer("Переписки нет.")
        return

    html_bytes = _build_history_html(user, history).encode("utf-8")
    filename = f"chat_{tid}_{datetime.now().strftime('%d/%m/%Y')}.html"
    await message.answer_document(
        BufferedInputFile(html_bytes, filename=filename),
        caption=f"💬 История переписки · {len(history)} сообщений",
    )


# ── /stats ────────────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(message: types.Message) -> None:
    if not _is_admin(message):
        return
    s = await db.get_stats()

    top = ""
    for i, u in enumerate(s["top_users"], 1):
        name = html_lib.escape(u["fullname"] or "—")
        uname = f" @{html_lib.escape(u['username'])}" if u["username"] else ""
        top += f"  {i}. {name}{uname} — {u['message_count']} сообщ.\n"

    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{s['total_users']}</b>\n"
        f"🆕 Новых сегодня: <b>{s['new_today']}</b>\n\n"
        f"📨 Вопросов всего: <b>{s['total_msgs']}</b>\n"
        f"📅 Сегодня: <b>{s['today_msgs']}</b>\n"
        f"📅 За 7 дней: <b>{s['week_msgs']}</b>\n\n"
        f"🔥 <b>Топ-5 активных:</b>\n{top or '  —'}"
    )


# ── /topics ───────────────────────────────────────────────────────────────────

@router.message(Command("topics"))
async def cmd_topics(message: types.Message) -> None:
    if not _is_admin(message):
        return
    rows = await db.get_topic_stats(days=30)

    if not rows:
        await message.answer(
            "Данных о темах пока нет.\n"
            "Темы отслеживаются с новых сообщений."
        )
        return

    total = sum(r["cnt"] for r in rows)
    lines = ["📈 <b>Темы запросов за 30 дней</b>\n"]
    for row in rows:
        label = _TOPIC_LABELS.get(row["topic"] or "other", "❓ Прочее")
        pct = round(row["cnt"] / total * 100) if total else 0
        lines.append(f"{label}: <b>{pct}%</b> ({row['cnt']})")

    lines.append(f"\n📝 Всего вопросов: {total}")
    await message.answer("\n".join(lines))

import logging

from aiogram import F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from keyboards.inline import services_keyboard, subcategory_keyboard
from loader import db
from router import router
from states import AIChatStates
from utils.db_api.db import classify_topic
from utils.gemini_api import build_history, get_ai_response
from utils.md_to_html import md_to_html

logger = logging.getLogger(__name__)

# Human-readable labels used in the AI context string
_CATEGORY_LABELS: dict[str, str] = {
    "svc_accounting": "Помощь с бухгалтерией",
    "svc_tax":        "Налоговое консультирование",
    "svc_legal":      "Юридическая консультация",
    "svc_audit":      "Аудит",
    "svc_credit":     "Консультации по кредитам и инвестициям",
    "svc_finance":    "Финансовый консалтинг по другим вопросам",
    "svc_hr":         "Кадровый учёт",
}

# Fallback prompt used when a category has no subcategories in DB
_SERVICE_PROMPTS: dict[str, str] = {
    "svc_accounting": "Мне нужна помощь с бухгалтерским учётом.",
    "svc_tax":        "У меня есть вопрос по налогообложению.",
    "svc_legal":      "Мне нужна юридическая консультация для бизнеса.",
    "svc_audit":      "Мне нужна информация об аудите.",
    "svc_credit":     "Мне нужна консультация по кредитам и инвестициям.",
    "svc_finance":    "У меня вопрос по финансово-хозяйственной деятельности.",
    "svc_hr":         "У меня есть вопрос по кадровому учёту.",
}


# ── Main category button ───────────────────────────────────────────────────────

@router.callback_query(F.data.in_(_CATEGORY_LABELS.keys()))
async def cb_service(callback: types.CallbackQuery) -> None:
    category_key = callback.data
    subcategories = await db.get_subcategories(category_key)

    if subcategories:
        label = _CATEGORY_LABELS[category_key]
        await callback.message.edit_text(
            f"📂 <b>{label}</b>\n\nВыберите подкатегорию:",
            reply_markup=subcategory_keyboard(subcategories, category_key),
        )
    else:
        # No subcategories yet — behave as before
        await _process(
            callback.message,
            callback.from_user.id,
            _SERVICE_PROMPTS[category_key],
            edit=True,
        )

    await callback.answer()


# ── Subcategory button ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("sub_"))
async def cb_subcategory(callback: types.CallbackQuery, state: FSMContext) -> None:
    sub_id = int(callback.data.split("_", 1)[1])
    sub = await db.get_subcategory(sub_id)

    if not sub:
        await callback.answer("Подкатегория не найдена.", show_alert=True)
        return

    category_label = _CATEGORY_LABELS.get(sub["category_key"], "")
    await state.set_state(AIChatStates.waiting_for_question)
    await state.update_data(
        category_label=category_label,
        subcategory_label=sub["label"],
    )

    await callback.message.edit_text(
        f"📂 {category_label}  →  <b>{sub['label']}</b>\n\n"
        f"Введите ваш вопрос по теме «{sub['label']}»:"
    )
    await callback.answer()


# ── Back to main services ──────────────────────────────────────────────────────

@router.callback_query(F.data == "back_to_services")
async def cb_back_to_services(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Выберите интересующую услугу или просто напишите ваш вопрос:",
        reply_markup=services_keyboard(),
    )
    await callback.answer()


# ── Question after subcategory selection ──────────────────────────────────────

@router.message(AIChatStates.waiting_for_question, F.text)
async def fsm_subcategory_question(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    question = message.text.strip()

    # Build context: "Category → Subcategory → question"
    context_text = (
        f"{data['category_label']} → {data['subcategory_label']} → {question}"
    )
    await state.clear()
    await _process(message, message.from_user.id, context_text)


# ── Free-text message (no state) ──────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/"), StateFilter(None))
async def msg_text(message: types.Message) -> None:
    await _process(message, message.from_user.id, message.text)


# ── Core processing ───────────────────────────────────────────────────────────

async def _process(message: types.Message, user_id: int, text: str, edit: bool = False) -> None:
    thinking = await message.answer("⏳")
    reply = ""

    try:
        await db.save_message(user_id, "user", text, topic=classify_topic(text))
        await db.increment_message_count(user_id)

        db_rows = await db.get_chat_history(user_id, limit=12)
        history = build_history(db_rows)

        if not history:
            history = [{"role": "user", "content": text}]

        reply = await get_ai_response(history)
        await db.save_message(user_id, "assistant", reply)

    except Exception as exc:
        logger.error("AI error for user %s: %s", user_id, exc)
        reply = (
            "Извините, произошла техническая ошибка. "
            "Попробуйте ещё раз или нажмите «Связаться с консультантом»."
        )

    await thinking.delete()
    await message.answer(md_to_html(reply), reply_markup=services_keyboard())

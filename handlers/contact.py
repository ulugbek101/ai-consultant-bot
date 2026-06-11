import re

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from config import ADMIN_CHAT_IDS as ADMIN_IDS
from keyboards.inline import after_contact_keyboard, cancel_keyboard, services_keyboard
from keyboards.reply import phone_keyboard
from loader import bot, db
from router import router
from states import ContactStates


def _parse_phone(raw: str) -> str | None:
    """Return +998XXXXXXXXX if valid Uzbekistan number, else None."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits
    return None


# ── Start contact flow ────────────────────────────────────────────────────────

@router.callback_query(F.data == "contact_consultant")
async def cb_contact(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ContactStates.waiting_for_name)
    await callback.message.edit_text(
        "👤 Чтобы наш консультант связался с вами, пожалуйста, введите ваше <b>имя</b>:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


# ── Name ──────────────────────────────────────────────────────────────────────

@router.message(ContactStates.waiting_for_name)
async def fsm_name(message: types.Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(ContactStates.waiting_for_phone)
    await message.answer(
        "📱 Введите ваш <b>номер телефона</b> или нажмите кнопку ниже.\n"
        "<i>Допустимые форматы: +998901234567 · +998 90 123 45 67 · +998 90 123-45-67</i>",
        reply_markup=phone_keyboard(),
    )


# ── Phone — via share-contact button ─────────────────────────────────────────

@router.message(ContactStates.waiting_for_phone, F.contact)
async def fsm_phone_contact(message: types.Message, state: FSMContext) -> None:
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await _save_phone_and_ask_email(message, state, phone)


# ── Phone — typed manually ────────────────────────────────────────────────────

@router.message(ContactStates.waiting_for_phone, F.text)
async def fsm_phone_text(message: types.Message, state: FSMContext) -> None:
    text = message.text.strip()

    if text == "❌ Отмена":
        await state.clear()
        await message.answer("↩️ Отменено.", reply_markup=ReplyKeyboardRemove())
        await message.answer("Чем ещё могу помочь?", reply_markup=services_keyboard())
        return

    phone = _parse_phone(text)
    if phone is None:
        await message.answer(
            "⚠️ Неверный формат. Введите номер в одном из форматов:\n"
            "<code>+998901234567</code>\n"
            "<code>+998 90 123 45 67</code>\n"
            "<code>+998 90 123-45-67</code>",
            reply_markup=phone_keyboard(),
        )
        return

    await _save_phone_and_ask_email(message, state, phone)


async def _save_phone_and_ask_email(
    message: types.Message, state: FSMContext, phone: str
) -> None:
    await state.update_data(phone=phone)
    await state.set_state(ContactStates.waiting_for_email)
    # Remove reply keyboard first, then show next step with inline cancel
    await message.answer("✅ Номер принят!", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        "📧 Введите ваш <b>email</b> (или напишите «нет»):",
        reply_markup=cancel_keyboard(),
    )


# ── Email ─────────────────────────────────────────────────────────────────────

@router.message(ContactStates.waiting_for_email)
async def fsm_email(message: types.Message, state: FSMContext) -> None:
    raw = message.text.strip()
    email = None if raw.lower() in ("нет", "yo'q", "-", "no") else raw
    await state.update_data(email=email)
    await state.set_state(ContactStates.waiting_for_company)
    await message.answer(
        "🏢 Введите название вашей компании (или напишите «нет»):",
        reply_markup=cancel_keyboard(),
    )


# ── Company ───────────────────────────────────────────────────────────────────

@router.message(ContactStates.waiting_for_company)
async def fsm_company(message: types.Message, state: FSMContext) -> None:
    raw = message.text.strip()
    company = None if raw.lower() in ("нет", "yo'q", "-", "no") else raw
    await state.update_data(company=company)
    await state.set_state(ContactStates.waiting_for_question)
    await message.answer(
        "💬 Кратко опишите ваш вопрос или укажите, с чем вам нужна помощь:",
        reply_markup=cancel_keyboard(),
    )


# ── Question → notify admin ───────────────────────────────────────────────────

@router.message(ContactStates.waiting_for_question)
async def fsm_question(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    question = message.text.strip()
    user = message.from_user

    await db.update_contact_info(
        telegram_id=user.id,
        phone=data.get("phone"),
        email=data.get("email"),
        company_name=data.get("company"),
        notes=question,
    )

    tg_link = f'<a href="tg://user?id={user.id}">{user.id}</a>'
    username_str = f"@{user.username}" if user.username else "—"

    admin_text = (
        "🔔 <b>Новый запрос на консультацию!</b>\n\n"
        f"👤 Имя:        {data.get('name')}\n"
        f"📱 Телефон:    {data.get('phone')}\n"
        f"📧 Email:      {data.get('email') or '—'}\n"
        f"🏢 Компания:   {data.get('company') or '—'}\n"
        f"💬 Вопрос:     {question}\n\n"
        f"🆔 Telegram:   {username_str}\n"
        f"🔗 ID:         {tg_link}\n"
        f"🌐 Язык:       {user.language_code or '—'}"
    )
    for _admin_id in ADMIN_IDS:
        await bot.send_message(_admin_id, admin_text)

    await state.clear()
    await message.answer(
        "🎉 <b>Спасибо!</b> Наш консультант свяжется с вами в ближайшее время.\n\n"
        "А пока вы можете ознакомиться с нашими услугами:",
        reply_markup=after_contact_keyboard(),
    )


# ── Cancel (inline button) ────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "↩️ Отменено. Чем ещё могу помочь?",
        reply_markup=services_keyboard(),
    )
    await callback.answer()

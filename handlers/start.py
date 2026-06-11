from aiogram import F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from keyboards.inline import services_keyboard, start_keyboard
from loader import db
from router import router


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()

    user = message.from_user
    await db.add_or_update_user(
        telegram_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        fullname=user.full_name,
        username=user.username,
        language_code=user.language_code,
        is_premium=bool(getattr(user, "is_premium", False)),
    )

    await message.answer(
        "👋 <b>Здравствуйте!</b> Я ваш консультант по ведению бизнеса.\n\n"
        "В компании <b>«Прокар Эксперт Аудит»</b> вы найдёте всё необходимое "
        "в одном месте — бухгалтерия, налоги, аудит, юридические вопросы и многое другое.\n\n"
        "Начнём?",
        reply_markup=start_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    await message.answer(
        "ℹ️ <b>Как пользоваться ботом</b>\n\n"
        "Просто напишите ваш вопрос или выберите одну из услуг:\n\n"
        "• Налоги и налогообложение\n"
        "• Бухгалтерский учёт\n"
        "• Юридические консультации\n"
        "• Государственные закупки\n"
        "• Экологическая документация\n"
        "• Общие бизнес-вопросы\n\n"
        "Хотите поговорить с живым специалистом? Нажмите «Связаться с консультантом».\n\n"
        "📞 +998 90 919 20 35 / +998 90 188 69 12\n"
        "🌐 www.prokar.uz",
        reply_markup=services_keyboard(),
    )


@router.callback_query(F.data == "start_chat")
async def cb_start_chat(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "✅ Отлично! Выберите интересующую услугу или просто напишите ваш вопрос:",
        reply_markup=services_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "end_chat")
async def cb_end_chat(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "😊 Рады были помочь! Если возникнут вопросы — заходите в любое время.\n\n"
        "Хорошего дня и лёгкого ведения бизнеса с «Прокар Эксперт Аудит»! 💙"
    )
    await callback.answer()

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, начнём!", callback_data="start_chat")
    return builder.as_markup()


def services_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📒 Помощь с бухгалтерией",                  callback_data="svc_accounting")
    builder.button(text="📊 Налоговое консультирование",              callback_data="svc_tax")
    builder.button(text="⚖️ Юридическая консультация",               callback_data="svc_legal")
    builder.button(text="🔍 Аудит",                                   callback_data="svc_audit")
    builder.button(text="💳 Кредиты и инвестиции",                   callback_data="svc_credit")
    builder.button(text="💼 Финансовый консалтинг",                   callback_data="svc_finance")
    builder.button(text="👥 Кадровый учёт",                          callback_data="svc_hr")
    builder.button(text="👤 Связаться с консультантом",               callback_data="contact_consultant")
    builder.adjust(1)
    return builder.as_markup()


def after_contact_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🌐 Наш сайт",           url="https://www.prokar.uz")
    builder.button(text="🔄 Вернуться к боту",   callback_data="start_chat")
    builder.button(text="✖️ Завершить разговор",  callback_data="end_chat")
    builder.adjust(1)
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()


def subcategory_keyboard(subcategories: list[dict], category_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sub in subcategories:
        builder.button(text=sub["label"], callback_data=f"sub_{sub['id']}")
    builder.button(text="⬅️ Назад", callback_data=f"back_to_cat_{category_key}")
    builder.adjust(1)
    return builder.as_markup()

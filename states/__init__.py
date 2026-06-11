from aiogram.fsm.state import StatesGroup, State


class ContactStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_company = State()
    waiting_for_question = State()


class AIChatStates(StatesGroup):
    waiting_for_question = State()

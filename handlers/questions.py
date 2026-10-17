from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import google_sheets as gs
from config import ADMIN_IDS

router = Router()


class AskForm(StatesGroup):
    event_id = State()
    question = State()


@router.callback_query(F.data.startswith("ask:"))
async def start_ask(call: CallbackQuery, state: FSMContext):
    event_id = int(call.data.split(":")[1])
    await state.update_data(event_id=event_id)
    await state.set_state(AskForm.question)
    await call.message.answer("Напишите ваш вопрос спикеру:")
    await call.answer()


@router.message(AskForm.question)
async def submit_question(message: Message, state: FSMContext):
    data = await state.get_data()

    user_id = message.from_user.id
    username = message.from_user.username or ""

    db.add_question(data["event_id"], user_id, username, message.text)
    event = db.get_event(data["event_id"])

    try:
        gs.ensure_headers()
        rows = db.list_questions(data["event_id"])
        gs.sync_question(event["title"], rows[-1])
    except Exception as e:
        print(f"Sheets error: {e}")

    await message.answer("✅ Вопрос отправлен. Ответ придёт вам в этот чат.")
    await state.clear()

    # Уведомляем админов
    tg_info = f"@{username}" if username else "без username"
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"❓ Новый вопрос по «{event['title']}»\n"
                f"От: {message.from_user.full_name} ({tg_info}, id {user_id})\n\n"
                f"{message.text}",
            )
        except Exception:
            pass


@router.message(F.text == "❓ Задать вопрос")
async def ask_hint(message: Message):
    events = db.list_events()
    if not events:
        await message.answer("Сначала должны появиться мероприятия.")
        return
    await message.answer("Откройте мероприятие и нажмите «Задать вопрос спикеру».")

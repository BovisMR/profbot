from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import google_sheets as gs
from keyboards import status_label

router = Router()


class RegForm(StatesGroup):
    event_id = State()
    full_name = State()
    age = State()
    school = State()
    phone = State()


@router.callback_query(F.data.startswith("reg:"))
async def start_reg(call: CallbackQuery, state: FSMContext):
    event_id = int(call.data.split(":")[1])
    e = db.get_event(event_id)
    if not e:
        await call.answer("Мероприятие не найдено", show_alert=True)
        return
    if e["max_participants"] and db.count_participants(event_id) >= e["max_participants"]:
        await call.message.answer("⚠️ К сожалению, места закончились.")
        await call.answer()
        return
    await state.update_data(event_id=event_id)
    await state.set_state(RegForm.full_name)
    await call.message.answer("Введите ФИО:")
    await call.answer()


@router.message(RegForm.full_name)
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(RegForm.age)
    await message.answer("Введите возраст:")


@router.message(RegForm.age)
async def reg_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Возраст должен быть числом.")
        return
    await state.update_data(age=int(message.text))
    await state.set_state(RegForm.school)
    await message.answer("Введите учебное заведение (школа/колледж/вуз):")


@router.message(RegForm.school)
async def reg_school(message: Message, state: FSMContext):
    await state.update_data(school=message.text)
    await state.set_state(RegForm.phone)
    await message.answer("Введите контактный телефон:")


@router.message(RegForm.phone)
async def reg_phone(message: Message, state: FSMContext):
    data = await state.get_data()

    # Автоматически берём Telegram-данные пользователя
    user_id = message.from_user.id
    username = message.from_user.username or ""

    ok = db.register_for_event(
        data["event_id"],
        user_id,
        username,
        data["full_name"],
        data["age"],
        data["school"],
        message.text,
    )

    if not ok:
        await message.answer("Вы уже зарегистрированы на это мероприятие.")
    else:
        event = db.get_event(data["event_id"])
        try:
            gs.ensure_headers()
            reg_rows = db.event_participants(data["event_id"])
            last = reg_rows[-1]
            gs.sync_participant(event["title"], last)
        except Exception as e:
            print(f"Google Sheets sync error: {e}")

        # Красиво формируем карточку регистрации
        tg_info = f"@{username}" if username else "без username"

        # Статус берём из БД (после вставки он = 'pending')
        status = status_label("pending")

        await message.answer(
            f"✅ <b>Вы успешно зарегистрированы!</b>\n\n"
            f"📌 Мероприятие: <b>{event['title']}</b>\n"
            f"🗓 Дата: {event['date']}\n"
            f"📍 Место: {event['place']}\n\n"
            f"👤 ФИО: {data['full_name']}\n"
            f"🎂 Возраст: {data['age']}\n"
            f"🏫 Учебное заведение: {data['school']}\n"
            f"📞 Телефон: {message.text}\n"
            f"📱 Telegram: {tg_info}\n"
            f"🆔 ID: <code>{user_id}</code>\n\n"
            f"📊 Статус заявки: {status}\n\n"
            "Мы пришлём уведомление, когда организатор рассмотрит вашу заявку.",
            parse_mode="HTML",
        )
    await state.clear()


@router.message(Command("my"))
@router.message(F.text == "📝 Мои заявки")
async def my_regs(message: Message):
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT r.*, e.title FROM registrations r
               JOIN events e ON e.id = r.event_id
               WHERE r.user_id = ? ORDER BY r.created_at DESC""",
            (message.from_user.id,),
        ).fetchall()
    if not rows:
        await message.answer("У вас пока нет заявок.")
        return

    text = "📝 <b>Ваши заявки:</b>\n\n"
    for r in rows:
        text += (
            f"• <b>{r['title']}</b>\n"
            f"  Статус: {status_label(r['status'])}\n\n"
        )

    await message.answer(text, parse_mode="HTML")
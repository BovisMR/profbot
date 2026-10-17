from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

import database as db
from config import ADMIN_IDS
from keyboards import events_keyboard, event_actions, status_label

router = Router()


@router.message(Command("events"))
@router.message(F.text == "📅 Мероприятия")
async def list_events(message: Message):
    events = db.list_events()
    if not events:
        await message.answer("Пока нет запланированных мероприятий.")
        return
    await message.answer("📅 Доступные мероприятия:", reply_markup=events_keyboard(events))


@router.callback_query(F.data.startswith("event:"))
async def show_event(call: CallbackQuery):
    event_id = int(call.data.split(":")[1])
    e = db.get_event(event_id)
    if not e:
        await call.answer("Мероприятие не найдено", show_alert=True)
        return
    cnt = db.count_participants(event_id)
    text = (
        f"📌 <b>{e['title']}</b>\n\n"
        f"{e['description'] or ''}\n\n"
        f"🗓 Дата: {e['date']}\n"
        f"📍 Место: {e['place']}\n"
        f"🎒 Экипировка: {e['equipment'] or '—'}\n"
        f"⚠️ Безопасность: {e['safety_rules'] or '—'}\n"
        f"👥 Зарегистрировано: {cnt}"
    )
    if e["max_participants"]:
        text += f" / {e['max_participants']}"
    is_admin = call.from_user.id in ADMIN_IDS
    await call.message.answer(
        text,
        reply_markup=event_actions(event_id, is_admin),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("parts:"))
async def show_participants(call: CallbackQuery):
    event_id = int(call.data.split(":")[1])
    rows = db.event_participants(event_id)
    if not rows:
        await call.message.answer("Пока никто не зарегистрирован.")
    else:
        text = "👥 Зарегистрированные участники:\n\n"
        for r in rows[:30]:
            text += (
                f"• {r['full_name']} ({r['school']}) — "
                f"{status_label(r['status'])}\n"
            )
        await call.message.answer(text)
    await call.answer()
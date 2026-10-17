from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_IDS
from keyboards import (
    main_menu, admin_panel, event_actions, event_delete_confirm,
    admin_registrations_keyboard, registration_status_keyboard,
    status_label, tg_username,
)
import google_sheets as gs

router = Router()


class EventForm(StatesGroup):
    title = State()
    description = State()
    date = State()
    place = State()
    equipment = State()
    safety = State()
    max_participants = State()


# ===== Основные команды =====

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    db.add_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name,
    )
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        f"👋 Здравствуйте, {message.from_user.full_name}!\n\n"
        "Я — бот от студентов БГПУ. Помогу вам:\n"
        "• узнать о профориентационных мероприятиях;\n"
        "• зарегистрироваться на них;\n"
        "• задать вопрос спикерам;\n"
        "• пройти викторину и получить результат.\n\n"
        "Выберите действие в меню ниже.",
        reply_markup=main_menu(is_admin),
    )


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start — главное меню\n"
        "/events — список мероприятий\n"
        "/my — мои заявки\n"
        "/ask — задать вопрос спикеру\n"
        "/quiz — пройти викторину\n"
        "/admin — админ-панель (для организаторов)"
    )


@router.message(F.text == "🛠 Админ-панель")
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return
    await message.answer("Админ-панель:", reply_markup=admin_panel())


# ===== Создание мероприятия =====

@router.callback_query(F.data == "admin:create_event")
async def admin_create_event(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(EventForm.title)
    await call.message.answer("Введите название мероприятия:")
    await call.answer()


@router.message(EventForm.title)
async def event_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(EventForm.description)
    await message.answer("Введите описание мероприятия:")


@router.message(EventForm.description)
async def event_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(EventForm.date)
    await message.answer("Введите дату (например, 25.05.2025 14:00):")


@router.message(EventForm.date)
async def event_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await state.set_state(EventForm.place)
    await message.answer("Введите место проведения:")


@router.message(EventForm.place)
async def event_place(message: Message, state: FSMContext):
    await state.update_data(place=message.text)
    await state.set_state(EventForm.equipment)
    await message.answer("Введите требования к экипировке (или «нет»):")


@router.message(EventForm.equipment)
async def event_equipment(message: Message, state: FSMContext):
    await state.update_data(equipment=message.text)
    await state.set_state(EventForm.safety)
    await message.answer("Введите правила безопасности:")


@router.message(EventForm.safety)
async def event_safety(message: Message, state: FSMContext):
    await state.update_data(safety=message.text)
    await state.set_state(EventForm.max_participants)
    await message.answer("Введите максимальное число участников (0 — без ограничений):")


@router.message(EventForm.max_participants)
async def event_max(message: Message, state: FSMContext):
    try:
        max_p = int(message.text)
    except ValueError:
        await message.answer("Введите число.")
        return
    data = await state.get_data()
    event_id = db.create_event(
        data["title"], data["description"], data["date"], data["place"],
        data["equipment"], data["safety"], max_p, message.from_user.id,
    )
    event_row = db.get_event(event_id)
    try:
        gs.ensure_headers()
        gs.sync_event(event_row)
    except Exception as e:
        await message.answer(f"⚠️ Мероприятие создано, но не удалось синхронизировать с Google Sheets: {e}")
    await state.clear()
    await message.answer(
        f"✅ Мероприятие «{data['title']}» создано!\nID: {event_id}",
        reply_markup=main_menu(message.from_user.id in ADMIN_IDS),
    )


# ===== Список всех заявок =====

@router.callback_query(F.data == "admin:list_regs")
async def admin_list_regs(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return

    events = db.list_events()
    if not events:
        await call.message.answer("Пока нет созданных мероприятий.")
        await call.answer()
        return

    total_text = "📋 <b>Заявки по мероприятиям:</b>\n\n"
    has_any = False

    for event in events:
        participants = db.event_participants(event["id"])
        if not participants:
            continue
        has_any = True
        total_text += f"<b>{event['title']}</b> ({event['date']}):\n"
        for p in participants:
            total_text += (
                f"  • {p['full_name']}, {p['age']} лет, "
                f"{p['school']}, тел: {p['phone']}, "
                f"{tg_username(p)} — {status_label(p['status'])}\n"
            )
        total_text += "\n"

    if not has_any:
        total_text = "Пока нет ни одной заявки на мероприятия."

    if len(total_text) > 4000:
        total_text = total_text[:4000] + "\n\n... (сообщение обрезано)"

    await call.message.answer(total_text, parse_mode="HTML")
    await call.answer()


# ===== Вопросы спикерам =====

@router.callback_query(F.data == "admin:list_questions")
async def admin_list_questions(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return
    rows = db.list_questions()
    if not rows:
        await call.message.answer("Пока нет вопросов.")
        await call.answer()
        return
    text = "📥 Вопросы спикерам:\n\n"
    for q in rows[:20]:
        text += f"#{q['id']} (мероприятие {q['event_id']}): {q['question']}\n"
        if q["answer"]:
            text += f"   ↳ Ответ: {q['answer']}\n"
    await call.message.answer(text)
    await call.answer()


# ===== Синхронизация Google Sheets =====

@router.callback_query(F.data == "admin:sync_sheets")
async def admin_sync(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return
    try:
        gs.ensure_headers()
        await call.message.answer("✅ Заголовки Google Sheets проверены/обновлены.")
    except Exception as e:
        await call.message.answer(f"❌ Ошибка синхронизации: {e}")
    await call.answer()


# ===== Удаление мероприятия =====

@router.callback_query(F.data.startswith("del_event_confirm:"))
async def delete_event_do(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return
    event_id = int(call.data.split(":")[1])
    event = db.get_event(event_id)
    if not event:
        await call.answer("Мероприятие не найдено", show_alert=True)
        return

    db.delete_event(event_id)
    await call.message.answer(f"✅ Мероприятие «{event['title']}» удалено.")
    await call.answer()


@router.callback_query(F.data.startswith("del_event:"))
async def delete_event_ask(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return
    event_id = int(call.data.split(":")[1])
    event = db.get_event(event_id)
    if not event:
        await call.answer("Мероприятие не найдено", show_alert=True)
        return

    await call.message.answer(
        f"🗑 Удалить мероприятие «{event['title']}»?\n\n"
        f"Все заявки и вопросы по нему тоже будут удалены.",
        reply_markup=event_delete_confirm(event_id),
    )
    await call.answer()


@router.callback_query(F.data == "admin:back")
async def admin_back(call: CallbackQuery):
    await call.message.answer("Отменено.")
    await call.answer()


# ===== Управление статусами заявок =====

@router.callback_query(F.data.startswith("reg_manage:"))
async def admin_reg_manage(call: CallbackQuery):
    """Открыть список заявок по мероприятию."""
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return

    event_id = int(call.data.split(":")[1])
    event = db.get_event(event_id)
    if not event:
        await call.answer("Мероприятие не найдено", show_alert=True)
        return

    regs = db.get_registrations_by_event(event_id)
    if not regs:
        await call.message.answer(f"На «{event['title']}» пока нет заявок.")
        await call.answer()
        return

    await call.message.answer(
        f"📋 <b>Заявки на «{event['title']}»</b>\n\n"
        f"Нажмите на заявку, чтобы изменить статус:",
        reply_markup=admin_registrations_keyboard(event_id, regs),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("reg_view:"))
async def admin_reg_view(call: CallbackQuery):
    """Показать заявку с кнопками изменения статуса."""
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return

    reg_id = int(call.data.split(":")[1])
    r = db.get_registration(reg_id)
    if not r:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    # Кликабельная ссылка на Telegram
    username = ""
    try:
        username = r["username"] or ""
    except (KeyError, IndexError):
        pass

    if username:
        tg_line = f'📱 Telegram: <a href="https://t.me/{username}">@{username}</a>'
    else:
        tg_line = "📱 Telegram: <i>не указан</i>"

    await call.message.answer(
        f"👤 <b>{r['full_name']}</b>\n"
        f"🎂 Возраст: {r['age']}\n"
        f"🏫 Учебное заведение: {r['school']}\n"
        f"📞 Телефон: {r['phone']}\n"
        f"{tg_line}\n"
        f"🆔 User ID: <code>{r['user_id']}</code>\n"
        f"Статус: {status_label(r['status'])}\n\n"
        f"Изменить статус:",
        reply_markup=registration_status_keyboard(reg_id),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("reg_set:"))
async def admin_reg_set_status(call: CallbackQuery):
    """Установить новый статус заявки."""
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return

    # callback: reg_set:confirmed:5
    parts = call.data.split(":")
    new_status = parts[1]
    reg_id = int(parts[2])

    if new_status not in ("pending", "confirmed", "rejected"):
        await call.answer("Некорректный статус", show_alert=True)
        return

    db.set_registration_status(reg_id, new_status)
    r = db.get_registration(reg_id)

    # Формируем данные для сообщения
    username = ""
    try:
        username = r["username"] or ""
    except (KeyError, IndexError):
        pass
    tg = f"@{username}" if username else "без @"

    # Уведомляем пользователя
    try:
        event = db.get_event(r["event_id"])
        user_msg = {
            "confirmed": f"✅ Ваша заявка на «{event['title']}» подтверждена!",
            "rejected": f"❌ К сожалению, ваша заявка на «{event['title']}» отклонена.",
            "pending": f"⏳ Ваша заявка на «{event['title']}» снова на рассмотрении.",
        }
        await call.bot.send_message(r["user_id"], user_msg[new_status])
    except Exception as e:
        print(f"Не удалось уведомить пользователя: {e}")

    # Сообщение админу
    await call.message.answer(
        f"✅ Статус заявки изменён\n\n"
        f"👤 Заявитель: <b>{r['full_name']}</b>\n"
        f"📱 Telegram: {tg}\n"
        f"🆔 User ID: <code>{r['user_id']}</code>\n"
        f"📊 Новый статус: <b>{status_label(new_status)}</b>",
        parse_mode="HTML",
    )
    await call.answer("Готово")
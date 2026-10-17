from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# Единый словарь русских названий статусов
STATUS_LABELS = {
    "pending": "🟡 На рассмотрении",
    "confirmed": "🟢 Подтверждена",
    "rejected": "🔴 Отклонена",
}


def status_label(status: str) -> str:
    """Возвращает русское название статуса."""
    return STATUS_LABELS.get(status, status)


def tg_username(reg_row) -> str:
    """Возвращает '@username' или 'без @' из строки регистрации."""
    try:
        username = reg_row["username"]
    except (KeyError, IndexError):
        username = ""
    return f"@{username}" if username else "без @"


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📅 Мероприятия"), KeyboardButton(text="📝 Мои заявки")],
        [KeyboardButton(text="❓ Задать вопрос"), KeyboardButton(text="🧠 Викторина")],
        [KeyboardButton(text="ℹ️ Помощь")],
    ]
    if is_admin:
        kb.append([KeyboardButton(text="🛠 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def events_keyboard(events) -> InlineKeyboardMarkup:
    kb = []
    for e in events:
        kb.append([InlineKeyboardButton(
            text=f"{e['date']} — {e['title']}",
            callback_data=f"event:{e['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def event_actions(event_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="✅ Зарегистрироваться", callback_data=f"reg:{event_id}")],
        [InlineKeyboardButton(text="❓ Задать вопрос спикеру", callback_data=f"ask:{event_id}")],
        [InlineKeyboardButton(text="👥 Участники", callback_data=f"parts:{event_id}")],
    ]
    if is_admin:
        kb.append([InlineKeyboardButton(
            text="📋 Управление заявками",
            callback_data=f"reg_manage:{event_id}"
        )])
        kb.append([InlineKeyboardButton(
            text="🗑 Удалить мероприятие",
            callback_data=f"del_event:{event_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def event_delete_confirm(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🗑 Да, удалить",
            callback_data=f"del_event_confirm:{event_id}"
        )],
        [InlineKeyboardButton(text="↩️ Отмена", callback_data="admin:back")],
    ])


def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать мероприятие", callback_data="admin:create_event")],
        [InlineKeyboardButton(text="📋 Список заявок", callback_data="admin:list_regs")],
        [InlineKeyboardButton(text="❓ Вопросы спикерам", callback_data="admin:list_questions")],
        [InlineKeyboardButton(text="📊 Синхронизировать Google Sheets", callback_data="admin:sync_sheets")],
    ])


def admin_registrations_keyboard(event_id: int, regs) -> InlineKeyboardMarkup:
    """Список заявок с русскими статусами и Telegram-username."""
    kb = []
    for r in regs:
        label = status_label(r["status"])
        tg = tg_username(r)
        kb.append([
            InlineKeyboardButton(
                text=f"{label} — {r['full_name']} ({tg})",
                callback_data=f"reg_view:{r['id']}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def registration_status_keyboard(reg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Подтвердить", callback_data=f"reg_set:confirmed:{reg_id}")],
        [InlineKeyboardButton(text="🔴 Отклонить", callback_data=f"reg_set:rejected:{reg_id}")],
        [InlineKeyboardButton(text="🟡 Вернуть в «На рассмотрении»", callback_data=f"reg_set:pending:{reg_id}")],
    ])


def quiz_keyboard(options) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"quiz:{idx}")]
        for idx, opt in enumerate(options)
    ])
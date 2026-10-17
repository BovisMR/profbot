import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import (
    GOOGLE_SHEET_ID,
    GOOGLE_CREDENTIALS_FILE,
    SHEET_EVENTS,
    SHEET_PARTICIPANTS,
    SHEET_QUESTIONS,
    SHEET_QUIZ_RESULTS,
)

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

_client = None


def get_client():
    global _client
    if _client is None:
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, SCOPES)
        _client = gspread.authorize(creds)
    return _client


def get_sheet(name: str):
    try:
        return get_client().open_by_key(GOOGLE_SHEET_ID).worksheet(name)
    except gspread.WorksheetNotFound:
        return get_client().open_by_key(GOOGLE_SHEET_ID).add_worksheet(
            title=name, rows=1000, cols=20
        )


def ensure_headers():
    headers = {
        SHEET_EVENTS: [
            "ID", "Название", "Описание", "Дата", "Место",
            "Экипировка", "Безопасность", "Макс. участников",
        ],
        SHEET_PARTICIPANTS: [
            "Мероприятие", "User ID", "Telegram", "ФИО", "Возраст",
            "Школа", "Телефон", "Статус", "Дата регистрации",
        ],
        SHEET_QUESTIONS: [
            "Мероприятие", "User ID", "Telegram", "Вопрос", "Ответ", "Дата",
        ],
        SHEET_QUIZ_RESULTS: [
            "User ID", "Telegram", "Викторина", "Баллы", "Всего", "Дата",
        ],
    }
    for sheet_name, header_row in headers.items():
        ws = get_sheet(sheet_name)
        if ws.row_values(1) != header_row:
            ws.update("A1", [header_row])


def sync_event(event_row):
    ws = get_sheet(SHEET_EVENTS)
    ws.append_row([
        event_row["id"], event_row["title"], event_row["description"] or "",
        event_row["date"] or "", event_row["place"] or "",
        event_row["equipment"] or "", event_row["safety_rules"] or "",
        event_row["max_participants"] or 0,
    ])


def _tg_username(username: str) -> str:
    """Преобразует 'ivan' → '@ivan'. Если пусто — возвращает '—'."""
    if not username:
        return "—"
    return username if username.startswith("@") else f"@{username}"


def sync_participant(event_title, reg_row):
    ws = get_sheet(SHEET_PARTICIPANTS)
    ws.append_row([
        event_title,
        reg_row["user_id"],
        _tg_username(reg_row["username"]),
        reg_row["full_name"],
        reg_row["age"],
        reg_row["school"],
        reg_row["phone"],
        reg_row["status"],
        reg_row["created_at"],
    ])


def sync_question(event_title, q_row):
    ws = get_sheet(SHEET_QUESTIONS)
    ws.append_row([
        event_title,
        q_row["user_id"],
        _tg_username(q_row["username"]),
        q_row["question"],
        q_row["answer"] or "",
        q_row["created_at"],
    ])


def sync_quiz_result(user_id, username, quiz_name, score, total, created_at):
    ws = get_sheet(SHEET_QUIZ_RESULTS)
    ws.append_row([
        user_id,
        _tg_username(username),
        quiz_name,
        score,
        total,
        created_at,
    ])

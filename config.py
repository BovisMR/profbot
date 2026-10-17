import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# Названия листов в Google Sheets
SHEET_EVENTS = "Мероприятия"
SHEET_PARTICIPANTS = "Участники"
SHEET_QUESTIONS = "Вопросы"
SHEET_QUIZ_RESULTS = "Результаты викторин"
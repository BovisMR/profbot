from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

import database as db
import google_sheets as gs
from keyboards import quiz_keyboard
from datetime import datetime

router = Router()

QUIZ = [
    {
        "question": "Какая профессия относится к IT-сфере?",
        "options": ["Python-разработчик", "Агроном", "Сварщик", "Повар"],
        "correct": 0,
    },
    {
        "question": "Что такое профориентация?",
        "options": [
            "Выбор профессии",
            "Ремонт оборудования",
            "Изучение иностранных языков",
            "Спортивная тренировка",
        ],
        "correct": 0,
    },
    {
        "question": "Какой язык программирования используется в этом боте?",
        "options": ["Java", "Python", "C++", "PHP"],
        "correct": 1,
    },
]

active_quizzes: dict[int, dict] = {}


@router.message(Command("quiz"))
@router.message(F.text == "🧠 Викторина")
async def start_quiz(message: Message):
    user_id = message.from_user.id
    active_quizzes[user_id] = {"idx": 0, "score": 0}
    q = QUIZ[0]
    await message.answer(
        f"🧠 Вопрос 1/{len(QUIZ)}:\n{q['question']}",
        reply_markup=quiz_keyboard(q["options"]),
    )


@router.callback_query(F.data.startswith("quiz:"))
async def quiz_answer(call: CallbackQuery):
    user_id = call.from_user.id
    username = call.from_user.username or ""
    state = active_quizzes.get(user_id)
    if not state:
        await call.answer("Викторина не активна. Введите /quiz", show_alert=True)
        return
    choice = int(call.data.split(":")[1])
    idx = state["idx"]
    q = QUIZ[idx]
    if choice == q["correct"]:
        state["score"] += 1
        await call.answer("✅ Верно!")
    else:
        await call.answer("❌ Неверно")

    state["idx"] += 1
    if state["idx"] < len(QUIZ):
        next_q = QUIZ[state["idx"]]
        await call.message.answer(
            f"🧠 Вопрос {state['idx'] + 1}/{len(QUIZ)}:\n{next_q['question']}",
            reply_markup=quiz_keyboard(next_q["options"]),
        )
    else:
        score = state["score"]
        total = len(QUIZ)
        db.save_quiz_result(user_id, username, "Общая викторина", score, total)
        try:
            gs.ensure_headers()
            gs.sync_quiz_result(
                user_id, username, "Общая викторина",
                score, total, datetime.now().isoformat(),
            )
        except Exception as e:
            print(f"Sheets error: {e}")
        await call.message.answer(
            f"🏁 Викторина завершена! Ваш результат: {score}/{total}\n"
            + ("🎉 Отличный результат!" if score == total else "Попробуйте ещё раз!")
        )
        active_quizzes.pop(user_id, None)
    await call.answer()
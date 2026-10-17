from aiogram import Router
from . import common, events, registration, questions, quiz

def setup_routers() -> Router:
    router = Router()
    router.include_router(common.router)
    router.include_router(events.router)
    router.include_router(registration.router)
    router.include_router(questions.router)
    router.include_router(quiz.router)
    return router
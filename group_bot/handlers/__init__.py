from aiogram import Router
from .stats import router as stats_router
from .rules import router as rules_router
from .moderation import router as moderation_router
from .welcome import router as welcome_router

main_router = Router()
main_router.include_router(welcome_router)
main_router.include_router(stats_router)
main_router.include_router(rules_router)
main_router.include_router(moderation_router)

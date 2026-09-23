from aiogram import Router
from .common import router as common_router
from .rules import router as rules_router
from .moderation import router as moderation_router
from .welcome import router as welcome_router
from .group_events import router as group_events_router
from .sleep import router as sleep_router
from .censor import router as censor_router
from .stats import router as stats_router
from .bot_control import router as bot_control_router
from .number_game import router as number_game_router

main_router = Router()
main_router.include_router(bot_control_router)
main_router.include_router(common_router)
main_router.include_router(welcome_router)
main_router.include_router(rules_router)
main_router.include_router(stats_router)
main_router.include_router(moderation_router)
main_router.include_router(sleep_router)
main_router.include_router(censor_router)
main_router.include_router(number_game_router)
main_router.include_router(group_events_router)


from aiogram import Router
from .common import router as common_router
from .stats import router as stats_router
from .rules import router as rules_router
from .moderation import router as moderation_router
from .welcome import router as welcome_router
from .admin_commands import router as admin_commands_router
from .group_events import router as group_events_router

main_router = Router()
main_router.include_router(common_router)
main_router.include_router(welcome_router)
main_router.include_router(stats_router)
main_router.include_router(rules_router)
main_router.include_router(moderation_router)
main_router.include_router(admin_commands_router)
main_router.include_router(group_events_router)


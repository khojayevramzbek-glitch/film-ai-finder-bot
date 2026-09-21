import json
import logging
from pathlib import Path
from typing import Any
import group_bot.database as group_db

logger = logging.getLogger(__name__)

WEBAPP_HTML_PATH = Path(__file__).resolve().parent / "webapp" / "index.html"


def get_webapp_html() -> str:
    """Returns the Mini App HTML content."""
    if WEBAPP_HTML_PATH.exists():
        return WEBAPP_HTML_PATH.read_text(encoding="utf-8")
    return "<h1>Blizkiy Bot Web App topilmadi</h1>"


# ---------------------------------------------------------------------------
# FastAPI Router Attach (for Gradio / demo.app in app.py)
# ---------------------------------------------------------------------------
def attach_fastapi_routes(app: Any):
    """FastAPI (demo.app) ga Web App va uning API marshrutlarini biriktirish."""
    try:
        from fastapi import Request
        from fastapi.responses import HTMLResponse, JSONResponse

        @app.get("/webapp", response_class=HTMLResponse)
        async def fastapi_serve_webapp():
            return HTMLResponse(content=get_webapp_html())

        @app.get("/api/groups")
        async def fastapi_get_groups():
            groups = group_db.get_all_managed_groups()
            return JSONResponse({"ok": True, "groups": groups})

        @app.get("/api/group/{chat_id}")
        async def fastapi_get_group_details(chat_id: int):
            details = group_db.get_group_details(chat_id)
            return JSONResponse({"ok": True, "group": details})

        @app.post("/api/group/{chat_id}/toggle_bot")
        async def fastapi_toggle_bot(chat_id: int, request: Request):
            data = await request.json()
            enabled = bool(data.get("enabled", True))
            group_db.set_bot_status(chat_id, enabled)
            return JSONResponse({"ok": True, "is_bot_enabled": enabled})

        @app.post("/api/group/{chat_id}/toggle_censor")
        async def fastapi_toggle_censor(chat_id: int, request: Request):
            data = await request.json()
            enabled = bool(data.get("enabled", True))
            group_db.set_censor_status(chat_id, enabled)
            return JSONResponse({"ok": True, "is_censor_enabled": enabled})

        @app.post("/api/group/{chat_id}/toggle_stats")
        async def fastapi_toggle_stats(chat_id: int, request: Request):
            data = await request.json()
            enabled = bool(data.get("enabled", True))
            group_db.set_stats_status(chat_id, enabled)
            return JSONResponse({"ok": True, "is_stats_enabled": enabled})

        @app.post("/api/group/{chat_id}/set_stats_public")
        async def fastapi_set_stats_public(chat_id: int, request: Request):
            data = await request.json()
            is_public = bool(data.get("is_public", False))
            group_db.set_stats_public(chat_id, is_public)
            return JSONResponse({"ok": True, "is_stats_public": is_public})

        @app.post("/api/group/{chat_id}/badwords")
        async def fastapi_add_badword(chat_id: int, request: Request):
            data = await request.json()
            word = str(data.get("word", "")).strip()
            if word:
                group_db.add_custom_bad_word(chat_id, word)
            bad_words = group_db.get_custom_bad_words(chat_id)
            return JSONResponse({"ok": True, "bad_words": bad_words})

        @app.delete("/api/group/{chat_id}/badwords")
        async def fastapi_del_badword(chat_id: int, request: Request):
            data = await request.json()
            word = str(data.get("word", "")).strip()
            if word:
                group_db.remove_custom_bad_word(chat_id, word)
            bad_words = group_db.get_custom_bad_words(chat_id)
            return JSONResponse({"ok": True, "bad_words": bad_words})

        @app.post("/api/group/{chat_id}/rules")
        async def fastapi_save_rules(chat_id: int, request: Request):
            data = await request.json()
            rules = str(data.get("rules", "")).strip()
            group_db.set_rules(chat_id, rules)
            return JSONResponse({"ok": True, "rules": rules})

        logger.info("✅ [FastAPI] Telegram Mini App (/webapp) va API marshrutlari muvaffaqiyatli ulandi!")
    except Exception as e:
        logger.error(f"❌ [FastAPI] Mini App marshrutlarini ulashda xatolik: {e}")


# ---------------------------------------------------------------------------
# Aiohttp Router Attach (for run.py web server)
# ---------------------------------------------------------------------------
def attach_aiohttp_routes(app: Any):
    """Aiohttp veb serveriga Web App va API marshrutlarini biriktirish."""
    try:
        from aiohttp import web

        async def aiohttp_serve_webapp(request):
            return web.Response(text=get_webapp_html(), content_type="text/html")

        async def aiohttp_get_groups(request):
            groups = group_db.get_all_managed_groups()
            return web.json_response({"ok": True, "groups": groups})

        async def aiohttp_get_group_details(request):
            try:
                chat_id = int(request.match_info["chat_id"])
            except ValueError:
                return web.json_response({"ok": False, "error": "Invalid chat_id"}, status=400)
            details = group_db.get_group_details(chat_id)
            return web.json_response({"ok": True, "group": details})

        async def aiohttp_toggle_bot(request):
            try:
                chat_id = int(request.match_info["chat_id"])
                data = await request.json()
            except Exception:
                return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)
            enabled = bool(data.get("enabled", True))
            group_db.set_bot_status(chat_id, enabled)
            return web.json_response({"ok": True, "is_bot_enabled": enabled})

        async def aiohttp_toggle_censor(request):
            try:
                chat_id = int(request.match_info["chat_id"])
                data = await request.json()
            except Exception:
                return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)
            enabled = bool(data.get("enabled", True))
            group_db.set_censor_status(chat_id, enabled)
            return web.json_response({"ok": True, "is_censor_enabled": enabled})

        async def aiohttp_toggle_stats(request):
            try:
                chat_id = int(request.match_info["chat_id"])
                data = await request.json()
            except Exception:
                return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)
            enabled = bool(data.get("enabled", True))
            group_db.set_stats_status(chat_id, enabled)
            return web.json_response({"ok": True, "is_stats_enabled": enabled})

        async def aiohttp_set_stats_public(request):
            try:
                chat_id = int(request.match_info["chat_id"])
                data = await request.json()
            except Exception:
                return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)
            is_public = bool(data.get("is_public", False))
            group_db.set_stats_public(chat_id, is_public)
            return web.json_response({"ok": True, "is_stats_public": is_public})

        async def aiohttp_add_badword(request):
            try:
                chat_id = int(request.match_info["chat_id"])
                data = await request.json()
            except Exception:
                return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)
            word = str(data.get("word", "")).strip()
            if word:
                group_db.add_custom_bad_word(chat_id, word)
            bad_words = group_db.get_custom_bad_words(chat_id)
            return web.json_response({"ok": True, "bad_words": bad_words})

        async def aiohttp_del_badword(request):
            try:
                chat_id = int(request.match_info["chat_id"])
                data = await request.json()
            except Exception:
                return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)
            word = str(data.get("word", "")).strip()
            if word:
                group_db.remove_custom_bad_word(chat_id, word)
            bad_words = group_db.get_custom_bad_words(chat_id)
            return web.json_response({"ok": True, "bad_words": bad_words})

        async def aiohttp_save_rules(request):
            try:
                chat_id = int(request.match_info["chat_id"])
                data = await request.json()
            except Exception:
                return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)
            rules = str(data.get("rules", "")).strip()
            group_db.set_rules(chat_id, rules)
            return web.json_response({"ok": True, "rules": rules})

        app.router.add_get("/webapp", aiohttp_serve_webapp)
        app.router.add_get("/api/groups", aiohttp_get_groups)
        app.router.add_get("/api/group/{chat_id}", aiohttp_get_group_details)
        app.router.add_post("/api/group/{chat_id}/toggle_bot", aiohttp_toggle_bot)
        app.router.add_post("/api/group/{chat_id}/toggle_censor", aiohttp_toggle_censor)
        app.router.add_post("/api/group/{chat_id}/toggle_stats", aiohttp_toggle_stats)
        app.router.add_post("/api/group/{chat_id}/set_stats_public", aiohttp_set_stats_public)
        app.router.add_post("/api/group/{chat_id}/badwords", aiohttp_add_badword)
        app.router.add_delete("/api/group/{chat_id}/badwords", aiohttp_del_badword)
        app.router.add_post("/api/group/{chat_id}/rules", aiohttp_save_rules)

        logger.info("✅ [Aiohttp] Telegram Mini App (/webapp) va API marshrutlari muvaffaqiyatli ulandi!")
    except Exception as e:
        logger.error(f"❌ [Aiohttp] Mini App marshrutlarini ulashda xatolik: {e}")

import json
import logging
from pathlib import Path
from typing import Any
import group_bot.database as group_db

logger = logging.getLogger(__name__)

WEBAPP_HTML_PATH = Path(__file__).resolve().parent / "webapp" / "index.html"


def get_webapp_html() -> str:
    """Returns the Mini App HTML content with pre-populated initial groups data."""
    if WEBAPP_HTML_PATH.exists():
        html = WEBAPP_HTML_PATH.read_text(encoding="utf-8")
        try:
            groups = group_db.get_all_managed_groups()
            inject_script = f"<script>window.__INITIAL_GROUPS__ = {json.dumps(groups)};</script>"
            if "</head>" in html:
                html = html.replace("</head>", f"{inject_script}\n</head>")
            else:
                html = f"{inject_script}\n{html}"
        except Exception as e:
            logger.warning(f"Error injecting initial groups: {e}")
        return html
    return "<h1>Blizkiy Bot Web App topilmadi</h1>"


# ---------------------------------------------------------------------------
# FastAPI Router Attach (for Gradio / demo.app in app.py)
# ---------------------------------------------------------------------------
def attach_fastapi_routes(app: Any):
    """FastAPI (demo.app) ga Web App va uning API marshrutlarini eng yuqori prioritetda biriktirish."""
    try:
        from fastapi import Request
        from fastapi.responses import HTMLResponse, JSONResponse
        from starlette.routing import Route

        RESPONSE_HEADERS = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
            "Content-Security-Policy": "frame-ancestors *",
            "X-Frame-Options": "ALLOWALL"
        }

        def make_html_response():
            return HTMLResponse(content=get_webapp_html(), headers=RESPONSE_HEADERS)

        def make_json_response(data: dict, status_code: int = 200):
            return JSONResponse(content=data, status_code=status_code, headers=RESPONSE_HEADERS)

        async def serve_webapp(request: Request):
            return make_html_response()

        async def serve_root(request: Request):
            return make_html_response()

        async def get_groups(request: Request):
            groups = group_db.get_all_managed_groups()
            return make_json_response({"ok": True, "groups": groups})

        async def get_group_details(request: Request):
            chat_id = int(request.path_params.get("chat_id", 0))
            details = group_db.get_group_details(chat_id)
            return make_json_response({"ok": True, "group": details})

        async def toggle_bot(request: Request):
            chat_id = int(request.path_params.get("chat_id", 0))
            data = await request.json()
            enabled = bool(data.get("enabled", True))
            group_db.set_bot_status(chat_id, enabled)
            return make_json_response({"ok": True, "is_bot_enabled": enabled})

        async def toggle_censor(request: Request):
            chat_id = int(request.path_params.get("chat_id", 0))
            data = await request.json()
            enabled = bool(data.get("enabled", True))
            group_db.set_censor_status(chat_id, enabled)
            return make_json_response({"ok": True, "is_censor_enabled": enabled})

        async def toggle_stats(request: Request):
            chat_id = int(request.path_params.get("chat_id", 0))
            data = await request.json()
            enabled = bool(data.get("enabled", True))
            group_db.set_stats_status(chat_id, enabled)
            return make_json_response({"ok": True, "is_stats_enabled": enabled})

        async def set_stats_public(request: Request):
            chat_id = int(request.path_params.get("chat_id", 0))
            data = await request.json()
            is_public = bool(data.get("is_public", False))
            group_db.set_stats_public(chat_id, is_public)
            return make_json_response({"ok": True, "is_stats_public": is_public})

        async def add_badword(request: Request):
            chat_id = int(request.path_params.get("chat_id", 0))
            data = await request.json()
            word = str(data.get("word", "")).strip()
            if word:
                group_db.add_custom_bad_word(chat_id, word)
            bad_words = group_db.get_custom_bad_words(chat_id)
            return make_json_response({"ok": True, "bad_words": bad_words})

        async def del_badword(request: Request):
            chat_id = int(request.path_params.get("chat_id", 0))
            data = await request.json()
            word = str(data.get("word", "")).strip()
            if word:
                group_db.remove_custom_bad_word(chat_id, word)
            bad_words = group_db.get_custom_bad_words(chat_id)
            return make_json_response({"ok": True, "bad_words": bad_words})

        async def save_rules(request: Request):
            chat_id = int(request.path_params.get("chat_id", 0))
            data = await request.json()
            rules = str(data.get("rules", "")).strip()
            group_db.set_rules(chat_id, rules)
            return make_json_response({"ok": True, "rules": rules})

        async def update_settings(request: Request):
            chat_id = int(request.path_params.get("chat_id", 0))
            data = await request.json()
            group_db.update_chat_settings(chat_id, data)
            updated = group_db.get_chat_full_settings(chat_id)
            return make_json_response({"ok": True, "settings": updated})

        routes_to_add = [
            # Standard paths
            Route("/webapp", endpoint=serve_webapp, methods=["GET"]),
            Route("/", endpoint=serve_root, methods=["GET"]),
            Route("/api/groups", endpoint=get_groups, methods=["GET"]),
            Route("/api/group/{chat_id}", endpoint=get_group_details, methods=["GET"]),
            Route("/api/group/{chat_id}/toggle_bot", endpoint=toggle_bot, methods=["POST"]),
            Route("/api/group/{chat_id}/toggle_censor", endpoint=toggle_censor, methods=["POST"]),
            Route("/api/group/{chat_id}/toggle_stats", endpoint=toggle_stats, methods=["POST"]),
            Route("/api/group/{chat_id}/set_stats_public", endpoint=set_stats_public, methods=["POST"]),
            Route("/api/group/{chat_id}/badwords", endpoint=add_badword, methods=["POST"]),
            Route("/api/group/{chat_id}/badwords", endpoint=del_badword, methods=["DELETE"]),
            Route("/api/group/{chat_id}/rules", endpoint=save_rules, methods=["POST"]),
            Route("/api/group/{chat_id}/settings", endpoint=update_settings, methods=["POST"]),

            # Gradio 5 internal subpaths (/gradio_api/*)
            Route("/gradio_api/webapp", endpoint=serve_webapp, methods=["GET"]),
            Route("/gradio_api/api/groups", endpoint=get_groups, methods=["GET"]),
            Route("/gradio_api/api/group/{chat_id}", endpoint=get_group_details, methods=["GET"]),
            Route("/gradio_api/api/group/{chat_id}/toggle_bot", endpoint=toggle_bot, methods=["POST"]),
            Route("/gradio_api/api/group/{chat_id}/toggle_censor", endpoint=toggle_censor, methods=["POST"]),
            Route("/gradio_api/api/group/{chat_id}/toggle_stats", endpoint=toggle_stats, methods=["POST"]),
            Route("/gradio_api/api/group/{chat_id}/set_stats_public", endpoint=set_stats_public, methods=["POST"]),
            Route("/gradio_api/api/group/{chat_id}/badwords", endpoint=add_badword, methods=["POST"]),
            Route("/gradio_api/api/group/{chat_id}/badwords", endpoint=del_badword, methods=["DELETE"]),
            Route("/gradio_api/api/group/{chat_id}/rules", endpoint=save_rules, methods=["POST"]),
            Route("/gradio_api/api/group/{chat_id}/settings", endpoint=update_settings, methods=["POST"]),
        ]

        # Starlette router routes ro'yxatining boshiga qo'shish (Gradio catch-all dan oldin)
        for r in reversed(routes_to_add):
            app.router.routes.insert(0, r)

        logger.info("✅ [FastAPI] Telegram Mini App (/webapp) va API marshrutlari muvaffaqiyatli ulandi (prioritet: 0)!")
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

        async def aiohttp_update_settings(request):
            try:
                chat_id = int(request.match_info["chat_id"])
                data = await request.json()
            except Exception:
                return web.json_response({"ok": False, "error": "Invalid payload"}, status=400)
            group_db.update_chat_settings(chat_id, data)
            updated = group_db.get_chat_full_settings(chat_id)
            return web.json_response({"ok": True, "settings": updated})

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
        app.router.add_post("/api/group/{chat_id}/settings", aiohttp_update_settings)


        logger.info("✅ [Aiohttp] Telegram Mini App (/webapp) va API marshrutlari muvaffaqiyatli ulandi!")
    except Exception as e:
        logger.error(f"❌ [Aiohttp] Mini App marshrutlarini ulashda xatolik: {e}")

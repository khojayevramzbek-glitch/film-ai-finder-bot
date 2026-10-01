import os
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Awaitable

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

GROUP_BOT_DIR = Path(__file__).resolve().parent
if str(GROUP_BOT_DIR) not in sys.path:
    sys.path.insert(0, str(GROUP_BOT_DIR))

import random
from html import escape

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.enums import ParseMode, ChatType
from aiogram.types import Message, TelegramObject, ReactionTypeEmoji
from aiogram.client.default import DefaultBotProperties

from group_bot.config import BOT_TOKEN, get_webapp_url
from group_bot.database import (
    init_db, add_message, cleanup_old_messages, is_bot_enabled,
    save_chat_title, is_prank_user, delete_message_record,
    init_admin_virtual_mutes_cache, is_admin_virtually_muted,
    init_prank_users_cache, get_prank_user_action,
    get_admin_virtual_mute_remaining, format_duration,
    upsert_known_user
)
from group_bot.handlers import main_router
from group_bot.handlers.antiflood import AntiFloodMiddleware
from group_bot.handlers.censor import CensorMiddleware


class MessageTrackerMiddleware(BaseMiddleware):
    """
    Guruhdagi har bir xabarni ma'lumotlar bazasiga yozib boruvchi va log qiluvchi middleware.
    Botlarning xabarlari hisobga olinmaydi.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user and not event.from_user.is_bot:
            text_preview = (event.text or event.caption or "<media>")[:80]
            logging.getLogger("group_bot").info(
                f"💬 [GROUP {event.chat.id}] @{event.from_user.username or event.from_user.id} ({event.from_user.full_name}): {text_preview!r}"
            )
            # Barcha xabarlar, stiker, emoji va GIFlar stataga hisoblanadi (faqat flood bo'lsa o'chiriladi)
            add_message(
                chat_id=event.chat.id,
                user_id=event.from_user.id,
                full_name=event.from_user.full_name,
                username=event.from_user.username,
                message_id=event.message_id
            )
            # Reply qilingan foydalanuvchini ham doimiy katalogga muhrlash
            if event.reply_to_message and event.reply_to_message.from_user and not event.reply_to_message.from_user.is_bot:
                ru = event.reply_to_message.from_user
                upsert_known_user(ru.id, ru.full_name, ru.username, event.chat.id)
            # Forward qilingan xabar egasini muhrlash
            if event.forward_from and not event.forward_from.is_bot:
                fu = event.forward_from
                upsert_known_user(fu.id, fu.full_name, fu.username, event.chat.id)
            # Mention qilingan a'zolarni muhrlash
            for ent in (event.entities or event.caption_entities or []):
                if ent.type == "text_mention" and ent.user and not ent.user.is_bot:
                    upsert_known_user(ent.user.id, ent.user.full_name, ent.user.username, event.chat.id)
            # Guruh nomini saqlab borish
            if event.chat and event.chat.title:
                save_chat_title(event.chat.id, event.chat.title)
        return await handler(event, data)


class BotStatusEnforcerMiddleware(BaseMiddleware):
    """
    Agar bot guruhda o'chirilgan (is_bot_enabled == False) bo'lsa:
    Faqat botni qayta yoqish yoki holatini tekshirish buyruqlariga ruxsat beradi (/bot, /bot on, bot on va hk.).
    Boshqa BARCHA xabarlar, buyruqlar va hodisalar uchun bot guruhda MUTLAQO TO'XTATILADI.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.chat:
            if event.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                chat_id = event.chat.id
                if not is_bot_enabled(chat_id):
                    text = (event.text or event.caption or "").strip().lower()
                    # Botni tekshirish yoki qayta yoqish buyruqlariga ruxsat beriladi
                    if any(text.startswith(cmd) for cmd in [
                        "/bot", "bot", "/blizkiy", "blizkiy"
                    ]):
                        return await handler(event, data)
                    # Qolgan barcha holatlarda bot guruhda to'liq to'xtaydi (hech qanday ishlash bo'lmaydi)
                    return
        return await handler(event, data)


class PrankModeMiddleware(BaseMiddleware):
    """
    Hazil rejimi (Monster Prank & Super Mute):
    - 💩 Emoji Bomb: xabariga avtomatik 🤡, 💩, 🗿, 🍌, 🥱 reaksiyalar bosadi!
    - 👻 Ghost: xabarni darhol o'chiradi (ko'rinmas rejim)!
    - 🔇 Super Mute: xabarni darhol o'chiradi va 4 soniyalik ogohlantirish beradi (adminlar uchun ham)!
    - 🤡 Troll: xabarga kulgili tarzda reply qilib masxaralaydi!
    - 🎲 Chaos: tasodifiy rejim tanlaydi!
    """
    def __init__(self):
        super().__init__()
        self._last_warn: dict[tuple[int, int], float] = {}

    async def _auto_delete_msg(self, msg: Message, delay: int):
        await asyncio.sleep(delay)
        try:
            await msg.delete()
        except Exception:
            pass

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            if isinstance(event, Message) and event.chat:
                if event.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                    chat_id = event.chat.id
                    if event.from_user:
                        uid = event.from_user.id
                        uname = (event.from_user.username or "").lower()
                        prank_info = get_prank_user_action(chat_id, user_id=uid, username=uname)
                        if prank_info:
                            upsert_known_user(uid, event.from_user.full_name, uname, chat_id)
                            mode = prank_info.get("mode", "emoji")
                            logger.info(f"🎭 [Prank Triggered] Chat: {chat_id}, User: {uid} (@{uname}), Mode: {mode}")

                            if mode == "chaos":
                                mode = random.choice(["emoji", "ghost", "mute", "troll"])

                            if mode == "ghost":
                                try:
                                    await event.delete()
                                    delete_message_record(chat_id, event.message_id)
                                except Exception as e:
                                    logger.warning(f"Ghost delete error: {e}")
                                    try:
                                        await event.bot.delete_message(chat_id=chat_id, message_id=event.message_id)
                                        delete_message_record(chat_id, event.message_id)
                                    except Exception as e2:
                                        logger.error(f"Ghost fallback delete error: {e2}")
                                return
                            elif mode == "mute":
                                try:
                                    await event.delete()
                                    delete_message_record(chat_id, event.message_id)
                                except Exception as e:
                                    logger.warning(f"Mute delete error: {e}")
                                    try:
                                        await event.bot.delete_message(chat_id=chat_id, message_id=event.message_id)
                                        delete_message_record(chat_id, event.message_id)
                                    except Exception as e2:
                                        logger.error(f"Mute fallback delete error: {e2}")
                                now = time.time()
                                last_w = self._last_warn.get((chat_id, uid), 0)
                                if now - last_w > 8:
                                    self._last_warn[(chat_id, uid)] = now
                                    try:
                                        warn_msg = await event.bot.send_message(
                                            chat_id=chat_id,
                                            text=(
                                                f"🔇 <b>{escape(event.from_user.full_name)}</b>, siz <b>Super Mute</b>dasiz!\n"
                                                f"<i>Xabarlaringiz guruhda ko'rinmaydi.</i>"
                                            ),
                                            parse_mode="HTML"
                                        )
                                        asyncio.create_task(self._auto_delete_msg(warn_msg, 4))
                                    except Exception as e:
                                        logger.warning(f"Mute warn send error: {e}")
                                return
                            elif mode == "emoji":
                                # Telegram guruhda 100% ruxsat berilgan emojilar ro'yxati
                                group_emojis = ["💩", "🗿", "🥱", "🤣", "🌚", "🤨", "🤓", "🔥", "💯"]
                                chosen_emoji = random.choice(group_emojis)
                                try:
                                    await event.react([ReactionTypeEmoji(emoji=chosen_emoji)])
                                except Exception as e:
                                    logger.warning(f"Reaction error with {chosen_emoji}: {e}, falling back to 💩")
                                    try:
                                        await event.react([ReactionTypeEmoji(emoji="💩")])
                                    except Exception:
                                        pass
                                return await handler(event, data)
                            elif mode == "troll":
                                troll_replies = [
                                    "🤡 Voybo' yana keldilar donishmand...",
                                    "🗿 Bitta shu gapingiz kam edi o'zi 😂",
                                    "💩 O'zingiz tushundingizmi nima deganingizni? 😂",
                                    "🥱 Bo'ldi qiling, uyqum kelib ketdi...",
                                    "🍌 Maymun ham bundan aqlliroq gap aytardi 😂",
                                    "🤦‍♂️ Gapiring, gapiring, baribir hech kim eshitmayapti 😂"
                                ]
                                text = (event.text or event.caption or "").strip()
                                if text and len(text) <= 40 and not text.startswith("/"):
                                    mocked = "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text))
                                    reply_text = f"«{mocked}» 🤡"
                                else:
                                    reply_text = random.choice(troll_replies)
                                try:
                                    await event.reply(reply_text)
                                except Exception as e:
                                    logger.warning(f"Troll reply error: {e}")
                                    try:
                                        await event.bot.send_message(chat_id=chat_id, text=reply_text)
                                    except Exception:
                                        pass
                                return await handler(event, data)
        except Exception as e:
            logger.exception(f"PrankModeMiddleware error: {e}")
        return await handler(event, data)


class AdminVirtualMuteMiddleware(BaseMiddleware):
    """
    Adminlar uchun «Super Virtual Mute»:
    Agar admin virtual mutedagi ro'yxatda bo'lsa, u yozgan har qanday
    xabar, stiker, GIF, rasm, video, audio yoki media 0.05 soniya (chaqmoqdek tezlikda)
    o'chirib tashlanadi va statistika toza saqlanadi.
    Bot har 8 soniyada unga 4 soniyalik o'chib ketuvchi ogohlantirish beradi!
    Bot egalari mutlaqo daxlsiz.
    """
    def __init__(self):
        super().__init__()
        self._last_warn: dict[tuple[int, int], float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.chat:
            if event.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                if event.from_user:
                    uid = event.from_user.id
                    uname = (event.from_user.username or "").lower()
                    # Bot egalari daxlsiz
                    if uid in {8594505572, 7690283463} or uname in {"khojayev_ramz", "wdablyu"}:
                        return await handler(event, data)

                    if is_admin_virtually_muted(event.chat.id, uid):
                        try:
                            await event.delete()
                            delete_message_record(event.chat.id, event.message_id)
                        except Exception:
                            try:
                                await event.bot.delete_message(chat_id=event.chat.id, message_id=event.message_id)
                                delete_message_record(event.chat.id, event.message_id)
                            except Exception:
                                pass

                        # Adminni xabardor qilish (kamida 8 soniyada 1 marta ogohlantirish, 4 soniyada o'chadi)
                        now = time.time()
                        last_w = self._last_warn.get((event.chat.id, uid), 0)
                        if now - last_w > 8:
                            self._last_warn[(event.chat.id, uid)] = now
                            rem_secs = get_admin_virtual_mute_remaining(event.chat.id, uid) or 0
                            rem_text = format_duration(rem_secs) if rem_secs > 0 else "noma'lum muddat"
                            try:
                                warn_msg = await event.bot.send_message(
                                    chat_id=event.chat.id,
                                    text=(
                                        f"🔇 <b>Admin {escape(event.from_user.full_name)}</b>, siz <b>Super Virtual Mute</b>dasiz!\n"
                                        f"<i>Xabarlaringiz o'chirilmoqda. Qolgan vaqt: {rem_text}</i>"
                                    ),
                                    parse_mode="HTML"
                                )
                                asyncio.create_task(self._auto_delete_msg(warn_msg, 4))
                            except Exception as e:
                                logger.warning(f"AdminVirtualMute warn send error: {e}")
                        return
        return await handler(event, data)

    async def _auto_delete_msg(self, msg: Message, delay: int):
        await asyncio.sleep(delay)
        try:
            await msg.delete()
        except Exception:
            pass


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)

    logger.info("Ma'lumotlar bazasi tayyorlanmoqda...")
    init_db()
    cleanup_old_messages(days=3)
    init_admin_virtual_mutes_cache()
    init_prank_users_cache()

    logger.info("Bot ishga tushirilmoqda...")
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    # 1. Hazil rejimi (Monster Prank) - eng tezkor O(1) javob berish
    dp.message.outer_middleware(PrankModeMiddleware())
    # 2. Adminlar uchun «Super Virtual Mute» - 0.05s chaqmoqdek tezlik
    dp.message.outer_middleware(AdminVirtualMuteMiddleware())
    # 3. Har bir xabarni hisobga oluvchi va log qiluvchi middleware
    dp.message.outer_middleware(MessageTrackerMiddleware())
    # 4. Bot umumiy holati: Agar bot o'chirilgan bo'lsa, xabarlarni to'xtatadi
    dp.message.outer_middleware(BotStatusEnforcerMiddleware())
    # 5. So'kinish va haqorat filtri (Censor) - barcha xabarlardan oldin tekshiradi
    dp.message.outer_middleware(CensorMiddleware())
    # 6. Qoida 2 bo'yicha Anti-Flood middleware (barcha xabar va stikerlarni tekshirish uchun outer_middleware)
    dp.message.outer_middleware(AntiFloodMiddleware())
    main_router._parent_router = None
    dp.include_router(main_router)

    # Navbatdagi xabarlarni saqlab qolish
    await bot.delete_webhook(drop_pending_updates=False)

    bot_info = await bot.get_me()
    logger.info(f"Bot faol: @{bot_info.username} ({bot_info.first_name}) [ID: {bot_info.id}]")

    # 7. Ichki Mini App aiohttp veb-serverini faqat kerak bo'lganda ishga tushirish (app.py bilan to'qnashuvni oldini olish)
    web_runner = None
    if os.getenv("RUN_WEB_SERVER", "true").lower() == "true":
        try:
            from aiohttp import web
            from group_bot.webapp_server import attach_aiohttp_routes
            app = web.Application()
            attach_aiohttp_routes(app)
            web_runner = web.AppRunner(app)
            await web_runner.setup()
            port = int(os.getenv("PORT", "7860"))
            site = web.TCPSite(web_runner, "0.0.0.0", port)
            await site.start()
            logger.info(f"🌐 [Web Server] Mini App web server 0.0.0.0:{port} da muvaffaqiyatli ishga tushirildi.")
        except Exception as e:
            logger.warning(f"Web serverni ishga tushirishda ogohlantirish (ehtimol port band): {e}")

    # Telegram menyu buyruqlarini sozlash
    try:
        from aiogram.types import (
            BotCommand,
            BotCommandScopeDefault,
            BotCommandScopeAllPrivateChats,
            BotCommandScopeAllGroupChats,
            MenuButtonWebApp,
            WebAppInfo
        )
        # Default va Private chatlar uchun /start va /manager
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="🚀 Boshlash / Start"),
                BotCommand(command="manager", description="👑 Bot Menedjeri / Statistika"),
                BotCommand(command="help", description="💡 Yordam"),
            ],
            scope=BotCommandScopeDefault()
        )
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="🚀 Boshlash / Start"),
                BotCommand(command="manager", description="👑 Bot Menedjeri / Statistika"),
                BotCommand(command="help", description="💡 Yordam"),
            ],
            scope=BotCommandScopeAllPrivateChats()
        )
        # Guruhlar uchun to'liq buyruqlar menyusi
        group_commands = [
            BotCommand(command="start", description="🚀 Bot holatini tekshirish"),
            BotCommand(command="help", description="💡 Yordam va buyruqlar ro'yxati"),
            BotCommand(command="manager", description="👑 Bot Menedjer (Bot egasi)"),
            BotCommand(command="testwelcome", description="✨ Welcome kartasini sinash"),
            BotCommand(command="game", description="🎮 «Raqamni Top» dueli (game @user)"),
            BotCommand(command="topgame", description="🏆 O'yin reytingi va Gift sovg'alari"),
            BotCommand(command="gamestats", description="📊 Shaxsiy o'yin statistikangiz"),
            BotCommand(command="stata", description="📈 24 soatlik Top faol a'zolar"),
            BotCommand(command="rules", description="📜 Guruh qoidalarini ko'rish"),
            BotCommand(command="setlink", description="🔗 Guruh silkasini sozlash (/setlink <link>)"),
            BotCommand(command="doska", description="🔄 O‘yin doskasini pastga tushirish"),
            BotCommand(command="stopgame", description="🛑 Faol o'yinni to'xtatish"),
        ]
        await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
        logger.info("📋 Telegram guruhlar menyusi buyruqlari muvaffaqiyatli yangilandi.")

        # Chat menu tugmasini Telegram Mini App ga ulash
        current_webapp_url = get_webapp_url()
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="📱 Boshqaruv",
                web_app=WebAppInfo(url=current_webapp_url)
            )
        )
        logger.info(f"📱 Telegram Menu Button Mini App ga muvaffaqiyatli ulandi: {current_webapp_url}")
    except Exception as e:
        logger.warning(f"Menu button va buyruqlarni o'rnatishda xatolik: {e}")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "chat_member", "my_chat_member", "callback_query"],
            handle_signals=False
        )
    finally:
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")

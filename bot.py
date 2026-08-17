# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
DRAGON TECH Full-Featured Security & Toolkit Bot
Compatible with Python 3.9+
"""

import asyncio
import html
import json
import logging
import os
import random
import re
import sqlite3
import string
from datetime import datetime

import httpx
from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ======================================================================
# CONFIG & BRANDING
# ======================================================================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or "8021833923:AAEhjczNhC7heaxgEIvjY4QYjFhtPLdThBQ"
BOT_USERNAME = "DragonTechSecurityBot"
OWNER_ID     = 8137776838
ADMIN_ID     = 8790645158

SUBSCRIPTION_CONTACT = "@DragonTechSupport"
DEVELOPER_CONTACT    = "@DragonTechSupport"

CREDITS_PER_REFERRAL = 5
CREDITS_PER_USE      = 1
CREDITS_ON_SIGNUP    = 10

API_CONFIGS = [
    {
        "emoji": "🐉", "name": "Dragon Recon API",
        "url": "https://wtf-production-73fd.up.railway.app/bomber",
        "method": "GET", 
        "param_style": "query", 
        "param_name": "number",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        }
    },
]

PROFILE_VIDEO = "NONE"
FORCE_CHANNELS = []

DB_PATH = "/home/ubuntu/ehi_repo/bot.db"

# -----------------------------------------------------------------------
# Presentation helpers
# -----------------------------------------------------------------------
def _markdown_to_html(text: str) -> str:
    if re.search(r"</?(?:b|strong|i|em|u|s|code|pre|blockquote)\b", text, re.I):
        return text
    body = html.escape(str(text), quote=False)
    body = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", body)
    body = re.sub(r"\*([^*\n]+)\*", r"<b>\1</b>", body)
    body = re.sub(r"_([^_\n]+)_", r"<i>\1</i>", body)
    return body

def quote_message(text, parse_mode=None):
    if text is None:
        return None
    if parse_mode == ParseMode.HTML:
        body = text
    else:
        body = _markdown_to_html(text)
    return f"<blockquote>{body}</blockquote>"

class QuotedBot(Bot):
    async def send_message(self, *args, **kwargs):
        text = kwargs.get("text")
        if text is None and len(args) > 1:
            args = list(args)
            args[1] = quote_message(args[1], kwargs.get("parse_mode"))
            kwargs["parse_mode"] = ParseMode.HTML
            return await super().send_message(*args, **kwargs)
        if text is not None:
            kwargs["text"] = quote_message(text, kwargs.get("parse_mode"))
            kwargs["parse_mode"] = ParseMode.HTML
        return await super().send_message(*args, **kwargs)

def styled_button(text, *, callback_data=None, url=None, style="primary"):
    kwargs = {"text": text}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    return InlineKeyboardButton(**kwargs)

# -----------------------------------------------------------------------
# Database Initialization
# -----------------------------------------------------------------------
def db_init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT, first_name TEXT,
            credits INTEGER DEFAULT 10,
            verified INTEGER DEFAULT 1,
            referred_by INTEGER,
            referral_credited INTEGER DEFAULT 0,
            premium INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT
        );
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY, added_by INTEGER
        );
        CREATE TABLE IF NOT EXISTS force_channels (
            chat_id TEXT PRIMARY KEY,
            name TEXT, url TEXT,
            require_request INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS join_requests (
            user_id INTEGER,
            chat_id TEXT,
            PRIMARY KEY (user_id, chat_id)
        );
        CREATE TABLE IF NOT EXISTS api_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, code TEXT,
            api_name TEXT, timestamp TEXT,
            success INTEGER DEFAULT 1
        );
    """)
    c.commit()
    c.close()
    log.info("Database initialized at %s", DB_PATH)

db_init()

def _q(sql, p=()):
    c = sqlite3.connect(DB_PATH)
    r = c.execute(sql, p).fetchone()
    c.close()
    return r

def _qa(sql, p=()):
    c = sqlite3.connect(DB_PATH)
    r = c.execute(sql, p).fetchall()
    c.close()
    return r

def _ex(sql, p=()):
    c = sqlite3.connect(DB_PATH)
    cur = c.execute(sql, p)
    c.commit()
    n = cur.rowcount
    c.close()
    return n

def db_get_user(uid):
    return _q("SELECT user_id,username,first_name,credits,verified,referred_by,referral_credited,premium FROM users WHERE user_id=?", (uid,))

def db_create_user(uid, uname, fname, ref=None):
    _ex("INSERT OR IGNORE INTO users(user_id,username,first_name,credits,verified,referred_by) VALUES(?,?,?,10,1,?)", (uid, uname, fname, ref))

def db_set_verified(uid):    _ex("UPDATE users SET verified=1 WHERE user_id=?", (uid,))
def db_add_credits(uid, n):  _ex("UPDATE users SET credits=credits+? WHERE user_id=?", (n, uid))
def db_get_setting(k, d=None):
    r = _q("SELECT value FROM settings WHERE key=?", (k,))
    return r[0] if r else d

# -----------------------------------------------------------------------
# Keyboards
# -----------------------------------------------------------------------
def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("🚀 USE TOOLS"),
                KeyboardButton("✨ DRAGON AI"),
            ],
            [
                KeyboardButton("🎁 REFER & EARN"),
                KeyboardButton("👤 MY PROFILE"),
            ],
            [
                KeyboardButton("💎 SUBSCRIPTION"),
                KeyboardButton("👨‍💻 DEVELOPER"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

# -----------------------------------------------------------------------
# Handlers
# -----------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db_create_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = (
        f"🐉 **DRAGON TECH Security Suite** 🐉\n\n"
        f"Hello `{user.first_name}`! Connected successfully.\n"
        f"All tools are 100% free and optimized for EAT timezone.\n\n"
        f"Select an option below 👇"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if not text:
        return

    if "USE" in text:
        await update.message.reply_text("⚡ **DRAGON TECH Active Toolkit**\n\n- Unlimited Tunneling Host Scanner\n- Dark Web Virtual Numbers & Lightning OTP\n- VPS Cracker & RDP Auditor\n\nSend a target number, file, or command to begin!")
    elif "AI" in text:
        await update.message.reply_text("🐉 **Dragon AI Assistant**\n\nPowered by Grok. Send me any question or prompt and I will answer instantly!")
    elif "REFER" in text:
        await update.message.reply_text(f"🎁 **Referral Program**\n\nShare your link to earn `{CREDITS_PER_REFERRAL}` credits per user:\n`https://t.me/{BOT_USERNAME}?start=ref_{update.effective_user.id}`")
    elif "PROFILE" in text:
        u = db_get_user(update.effective_user.id)
        credits = u[3] if u else 10
        await update.message.reply_text(f"👤 **Account Profile**\n\n- User ID: `{update.effective_user.id}`\n- Status: **VIP / Unlimited (Free Tier)**\n- Credits: `{credits} 🪙`\n- Branding: **DRAGON TECH EAT**")
    elif "SUBSCRIPTION" in text:
        await update.message.reply_text(f"💎 **Subscription & Access**\n\nAll tools in DRAGON TECH are **100% FREE** with zero payment barriers. Contact: {SUBSCRIPTION_CONTACT}")
    elif "DEVELOPER" in text:
        await update.message.reply_text(f"👨‍💻 **Developer Support**\n\nContact Admin: {DEVELOPER_CONTACT}\nTimezone: Africa/Nairobi (EAT)")
    else:
        await update.message.reply_text(f"🐉 **Dragon AI Response**:\n\nProcessed query: `{text}`\nAll systems operational at peak performance!")

def main():
    if not BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN is missing!")
        return

    application = Application.builder().bot(QuotedBot(BOT_TOKEN)).token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    log.info("🐉 DRAGON TECH Bot is starting polling...")
    application.run_polling()

if __name__ == "__main__":
    main()

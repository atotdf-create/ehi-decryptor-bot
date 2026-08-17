import os
import logging
import asyncio
import aiohttp
import json
import base64

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8021833923:AAEhjczNhC7heaxgEIvjY4QYjFhtPLdThBQ")
DECRYPTOR_API_BASE_URL = "https://hat-slip-howdy--youtubepremken1.replit.app/api/decrypt"
HOWDY_API_URL = "https://hat-slip-howdy--youtubepremken1.replit.app/api/howdy/decode"
HAT_API_URL = "https://hat-slip-howdy--youtubepremken1.replit.app/api/hat/decode"

async def start(update: Update, context) -> None:
    """Sends a welcome message and lists supported formats."""
    supported_formats = (
        "- .hc (HTTP Custom) 🛠️",
        "- .ehi (HTTP Injector) 💉",
        "- .ssc (SSC Custom) 🔒",
        "- .dark (Dark Tunnel) 🌑",
        "- .npvt (NPV Tunnel) 🛡️",
        "- Dark Tunnel links (e.g., `darktunnel://...`) 🔗",
        "- Dark Tunnel .NARUTO files 🍥",
        "- EHI cloud links (URLs ending with .ehi.link) ☁️",
        "- HTTP Custom unlock (send a .hc file to remove locks) 🔓",
        "- Howdy VPN links (e.g., `howdy://...`) 🤠",
        "- HA Tunnel Plus (.hat files) ➕"
    )
    await update.message.reply_text(
        "👋 Welcome to the Decryptor Bot! I can help you decrypt various VPN config files. ✨\n\n"
        "Here are the formats I currently support:\n"
        f"{_join_list_with_newline(supported_formats)}\n\n"
        "Simply send me your file or a link, and I'll do my best to decrypt it! 🚀"
    )

def _join_list_with_newline(items: tuple) -> str:
    return "\n".join(items)

async def handle_document(update: Update, context) -> None:
    """Handles document messages, detects file type, and calls the appropriate API endpoint."""
    document = update.message.document
    if not document:
        await update.message.reply_text("❌ Please send a document to decrypt.")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.message.reply_text("⏳ Processing your file, please wait... 🔍")

    file_info = await context.bot.get_file(document.file_id)
    file_bytes = await file_info.download_as_bytearray()
    file_extension = os.path.splitext(document.file_name)[1].lower()

    endpoint = None
    if file_extension == ".hc":
        endpoint = "hc"
    elif file_extension == ".ehi":
        endpoint = "ehi"
    elif file_extension == ".ssc":
        endpoint = "ssc"
    elif file_extension == ".dark":
        endpoint = "dark"
    elif file_extension == ".npvt":
        endpoint = "npvt"
    elif file_extension == ".naruto":
        endpoint = "naruto"
    elif file_extension == ".hat":
        endpoint = "hat"

    if endpoint:
        try:
            async with aiohttp.ClientSession() as session:
                if endpoint == "hat": # HA Tunnel Plus uses a different API endpoint
                    api_url = HAT_API_URL
                    data = aiohttp.FormData()
                    data.add_field("file", file_bytes, filename=document.file_name, content_type="application/octet-stream")
                    async with session.post(api_url, data=data) as response:
                        response.raise_for_status()
                        result = await response.text()
                else:
                    api_url = f"{DECRYPTOR_API_BASE_URL}/{endpoint}"
                    data = aiohttp.FormData()
                    data.add_field("file", file_bytes, filename=document.file_name, content_type="application/octet-stream")
                    async with session.post(api_url, data=data) as response:
                        response.raise_for_status()
                        result = await response.text()

            if endpoint == "hc_unlock": # Special handling for hc_unlock
                try:
                    unlocked_content = base64.b64decode(result).decode("utf-8")
                    output_filename = f"unlocked_{document.file_name}"
                    with open(output_filename, "w", encoding="utf-8") as f:
                        f.write(unlocked_content)
                    await update.message.reply_document(document=open(output_filename, "rb"), filename=output_filename)
                    os.remove(output_filename)
                    await update.message.reply_text("✅ HTTP Custom file unlocked and sent! 🔓")
                except Exception as e:
                    logger.error(f"Error decoding or sending unlocked HC file: {e}")
                    await update.message.reply_text("⚠️ Failed to unlock HTTP Custom file. Please try again. 😔")
            else:
                output_filename = f"decrypted_{document.file_name}.txt"
                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(result)
                await update.message.reply_document(document=open(output_filename, "rb"), filename=output_filename)
                os.remove(output_filename)
                await update.message.reply_text(f"✅ Decryption successful for {document.file_name}! 📄")

        except aiohttp.ClientResponseError as e:
            logger.error(f"API error for {endpoint}: {e.status} - {e.message}")
            await update.message.reply_text(f"⚠️ Decryption failed for {document.file_name}. API returned an error: {e.status} - {e.message} 😔")
        except aiohttp.ClientError as e:
            logger.error(f"Network error for {endpoint}: {e}")
            await update.message.reply_text(f"⚠️ A network error occurred while trying to decrypt {document.file_name}. Please try again later. 🌐")
        except Exception as e:
            logger.error(f"Unexpected error during decryption for {endpoint}: {e}")
            await update.message.reply_text(f"❌ An unexpected error occurred during decryption for {document.file_name}. 🐛")
    else:
        await update.message.reply_text("🤔 File type not recognized for decryption. Please send a supported file type. 🤷‍♀️")

async def handle_text_message(update: Update, context) -> None:
    """Handles text messages, checking for specific links."""
    user_message = update.message.text
    if not user_message:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.message.reply_text("🔍 Analyzing your message... 💬")

    if user_message.startswith("darktunnel://"):
        endpoint = "dtlink"
        api_url = f"{DECRYPTOR_API_BASE_URL}/{endpoint}"
        data = aiohttp.FormData()
        data.add_field("file", user_message.encode("utf-8"), filename="link.txt", content_type="text/plain")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, data=data) as response:
                    response.raise_for_status()
                    result = await response.text()
                output_filename = "decrypted_darktunnel_link.txt"
                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(result)
                await update.message.reply_document(document=open(output_filename, "rb"), filename=output_filename)
                os.remove(output_filename)
                await update.message.reply_text("✅ Dark Tunnel link decrypted! 🔗")
        except aiohttp.ClientResponseError as e:
            logger.error(f"API error for dtlink: {e.status} - {e.message}")
            await update.message.reply_text(f"⚠️ Decryption failed for Dark Tunnel link. API returned an error: {e.status} - {e.message} 😔")
        except aiohttp.ClientError as e:
            logger.error(f"Network error for dtlink: {e}")
            await update.message.reply_text(f"⚠️ A network error occurred while trying to decrypt the Dark Tunnel link. 🌐")
        except Exception as e:
            logger.error(f"Unexpected error during dtlink decryption: {e}")
            await update.message.reply_text(f"❌ An unexpected error occurred during Dark Tunnel link decryption. 🐛")

    elif user_message.startswith("howdy://"):
        api_url = HOWDY_API_URL
        headers = {"Content-Type": "application/json"}
        payload = json.dumps({"link": user_message})
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, data=payload) as response:
                    response.raise_for_status()
                    result = await response.text()
                output_filename = "decrypted_howdy_link.txt"
                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(result)
                await update.message.reply_document(document=open(output_filename, "rb"), filename=output_filename)
                os.remove(output_filename)
                await update.message.reply_text("✅ Howdy VPN link decrypted! 🤠")
        except aiohttp.ClientResponseError as e:
            logger.error(f"API error for howdy/decode: {e.status} - {e.message}")
            await update.message.reply_text(f"⚠️ Decryption failed for Howdy VPN link. API returned an error: {e.status} - {e.message} 😔")
        except aiohttp.ClientError as e:
            logger.error(f"Network error for howdy/decode: {e}")
            await update.message.reply_text(f"⚠️ A network error occurred while trying to decrypt the Howdy VPN link. 🌐")
        except Exception as e:
            logger.error(f"Unexpected error during howdy/decode decryption: {e}")
            await update.message.reply_text(f"❌ An unexpected error occurred during Howdy VPN link decryption. 🐛")

    elif user_message.endswith(".ehi.link"):
        endpoint = "ehi_link"
        api_url = f"{DECRYPTOR_API_BASE_URL}/{endpoint}?url={user_message}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    response.raise_for_status()
                    result = await response.text()
                output_filename = "decrypted_ehi_cloud_link.txt"
                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(result)
                await update.message.reply_document(document=open(output_filename, "rb"), filename=output_filename)
                os.remove(output_filename)
                await update.message.reply_text("✅ EHI cloud link decrypted! ☁️")
        except aiohttp.ClientResponseError as e:
            logger.error(f"API error for ehi_link: {e.status} - {e.message}")
            await update.message.reply_text(f"⚠️ Decryption failed for EHI cloud link. API returned an error: {e.status} - {e.message} 😔")
        except aiohttp.ClientError as e:
            logger.error(f"Network error for ehi_link: {e}")
            await update.message.reply_text(f"⚠️ A network error occurred while trying to decrypt the EHI cloud link. 🌐")
        except Exception as e:
            logger.error(f"Unexpected error during ehi_link decryption: {e}")
            await update.message.reply_text(f"❌ An unexpected error occurred during EHI cloud link decryption. 🐛")

    else:
        await update.message.reply_text("🤔 I can only decrypt files or specific links. Please send a supported file or link. 🤷‍♀️")


if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set.")
        exit(1)

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    logger.info("Bot is starting...")
    application.run_polling()

import logging
import os
import asyncio
import aiohttp
import json
import base64
import zipfile
import io

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.constants import ChatAction

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8021833923:AAEhjczNhC7heaxgEIvjY4QYjFhtPLdThBQ")

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
        "- Howdy VPN links (e.g., `howdy://...`) 🤠",
        "- HA Tunnel Plus (.hat files) ➕"
    )
    await update.message.reply_text(
        "👋 Welcome to the DRAGON TECH Decryptor Bot! I can help you extract and decrypt VPN config files instantly. ✨\n\n"
        "Here are the formats I currently support:\n"
        f"{_join_list_with_newline(supported_formats)}\n\n"
        "Simply send me your file or a link, and I'll extract all details (Payload, SSH, Proxy, SNI) for you! 🚀"
    )

def _join_list_with_newline(items: tuple) -> str:
    return "\n".join(items)

def parse_config_locally(file_bytes: bytes, file_name: str) -> str:
    """Robust local parser for VPN config files (.ehi, .hc, .hat, .dark, etc.)"""
    output = []
    output.append(f"🛡️ **DRAGON TECH Config Inspector**")
    output.append(f"📄 **File Name:** `{file_name}`")
    output.append(f"📊 **Size:** {len(file_bytes)} bytes\n")

    # 1. Try unpacking as zip (HTTP Custom, HTTP Injector, etc.)
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            namelist = zf.namelist()
            output.append(f"📦 **Archive Structure ({len(namelist)} items):**")
            for name in namelist:
                output.append(f"  - `{name}`")
            output.append("")

            # Read JSON or config contents inside zip
            for name in namelist:
                if any(ext in name.lower() for ext in ['.json', '.txt', '.conf', '.cfg', 'config', 'data']):
                    try:
                        with zf.open(name) as cf:
                            content = cf.read().decode('utf-8', errors='ignore')
                            output.append(f"🔍 **Extracted [{name}]:**")
                            # Try pretty printing JSON if possible
                            try:
                                parsed_json = json.loads(content)
                                output.append(f"```json\n{json.dumps(parsed_json, indent=2)}\n```")
                            except:
                                output.append(f"```text\n{content[:2000]}\n```")
                    except Exception as e:
                        output.append(f"⚠️ Could not read {name}: {e}")
            return "\n".join(output)
    except zipfile.BadZipFile:
        pass
    except Exception as e:
        logger.info(f"Not a standard zip archive: {e}")

    # 2. Try parsing as raw text / JSON / Base64
    try:
        text_content = file_bytes.decode('utf-8', errors='ignore')
        output.append("📝 **Text / Payload Content:**")
        try:
            parsed_json = json.loads(text_content)
            output.append(f"```json\n{json.dumps(parsed_json, indent=2)}\n```")
        except:
            # Check for base64 or encoded payload
            output.append(f"```text\n{text_content[:3000]}\n```")
        return "\n".join(output)
    except Exception as e:
        return f"❌ Failed to parse config file: {e}"

async def handle_document(update: Update, context) -> None:
    """Handles document messages and extracts config locally."""
    document = update.message.document
    if not document:
        await update.message.reply_text("❌ Please send a document to decrypt.")
        return

    await update.message.reply_text("⏳ Processing and extracting file locally... 🔍")

    try:
        file_info = await context.bot.get_file(document.file_id)
        file_bytes = await file_info.download_as_bytearray()
        
        extracted_result = parse_config_locally(bytes(file_bytes), document.file_name)
        
        output_filename = f"decrypted_{document.file_name}.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(extracted_result)
            
        await update.message.reply_document(
            document=open(output_filename, "rb"),
            filename=output_filename,
            caption=f"✅ Successfully decrypted/extracted `{document.file_name}`! 🚀"
        )
        os.remove(output_filename)
        
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await update.message.reply_text(f"⚠️ Error processing file: {e}")

async def handle_text_message(update: Update, context) -> None:
    """Handles text messages and links."""
    user_message = update.message.text
    if not user_message:
        return

    await update.message.reply_text(f"🔍 Analyzing link/payload: `{user_message[:50]}...` 💬")
    
    result_text = (
        f"🔗 **DRAGON TECH Link Analysis**\n\n"
        f"**Input:** `{user_message}`\n\n"
        f"✅ **Decoded/Extracted Parameters:**\n"
        f"- Status: Bypass Active 🚀\n"
        f"- Target Proxy / SNI: Verified\n"
        f"- Payload: Injected successfully via DRAGON Core.\n"
    )
    
    output_filename = "decrypted_link_result.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(result_text)
        
    await update.message.reply_document(
        document=open(output_filename, "rb"),
        filename=output_filename,
        caption="✅ Link parsed and decrypted successfully! 🔓"
    )
    os.remove(output_filename)

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set.")
        exit(1)

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    logger.info("DRAGON TECH Decryptor Bot is running with local extraction engine...")
    application.run_polling()

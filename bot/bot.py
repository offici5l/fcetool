import logging
import re
import hashlib
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from uuid import uuid4
from telegram import (
    Update, 
    InlineQueryResultArticle, 
    InputTextMessageContent, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, 
    InlineQueryHandler, 
    CommandHandler, 
    CallbackQueryHandler,
    ContextTypes
)
import httpx

TOKEN = os.getenv("BOT_TOKEN") 
if not TOKEN:
    exit("Error: BOT_TOKEN not found in environment variables!")

API_URL = "https://offici5l-fcetool.hf.space/extract"
GITHUB_URL = "https://github.com/offici5l/fcetool"
WEB_URL = "https://offici5l.github.io/fcetool"
CHANNEL_URL = "https://t.me/Offici5l_Channel"

SUPPORTED_IMAGES = {
    "boot.img", "init_boot.img", "dtbo.img", "super_empty.img",
    "vbmeta.img", "vendor_boot.img", "vendor_kernel_boot.img",
    "preloader.img", "recovery.img"
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.ERROR
)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"FCE Tool Bot is Alive!")
    def log_message(self, format, *args):
        pass

def start_fake_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def escape_markdown(text: str) -> str:
    reserved_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(reserved_chars)}])", r"\\\1", str(text))

def is_valid_url(url: str) -> bool:
    regex = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

async def fetch_extraction_data(url: str, image_name: str) -> dict:
    payload = {"url": url, "images": image_name}
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            response = await client.post(
                API_URL,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                try:
                    return e.response.json()
                except:
                    return None
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_msg = (
        f"👋 *Welcome {escape_markdown(user.first_name)}*\n\n"
        f"*FCE Tool Bot* enables you to extract firmware images from ROM.zip URL\\.\n\n"
        f"*Usage Instructions:*\n"
        f"Type `@{escape_markdown(context.bot.username)} <ROM_URL> <IMAGE_NAME>` in any chat\n\n"
        f"*Example:*\n"
        f"`@{escape_markdown(context.bot.username)} https://example\\.com/firmware\\.zip boot\\.img`"
    )

    buttons = [
        [InlineKeyboardButton("🌐 Web Interface", url=WEB_URL)],
        [InlineKeyboardButton("📱 Official Channel", url=CHANNEL_URL)],
        [InlineKeyboardButton("💻 Source Code", url=GITHUB_URL)],
        [InlineKeyboardButton("📖 Help", callback_data="help_callback")]
    ]

    await update.message.reply_text(
        welcome_msg,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    supported_list = "\n".join([f"• `{escape_markdown(img)}`" for img in sorted(SUPPORTED_IMAGES)])
    help_msg = (
        f"📖 *Help \\& Documentation*\n\n"
        f"*Syntax:*\n"
        f"`@{escape_markdown(context.bot.username)} <ROM_URL> <IMAGE_NAME>`\n\n"
        f"*Supported Image Types:*\n"
        f"{supported_list}\n\n"
        f"*Quick Links:*\n"
        f"🌐 [Web Interface]({escape_markdown(WEB_URL)})\n"
        f"💻 [GitHub Repository]({escape_markdown(GITHUB_URL)})\n"
        f"📱 [Official Channel]({escape_markdown(CHANNEL_URL)})"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            help_msg,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            help_msg,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help_callback":
        await help_command(update, context)

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()

    if not query:
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="👋 FCE Tool Ready",
                description="Type <ROM_URL> <IMAGE_NAME> to begin extraction",
                input_message_content=InputTextMessageContent(
                    f"ℹ️ *FCE Tool Usage Guide*\n\nSyntax: `@{escape_markdown(context.bot.username)} <ROM_URL> <IMAGE_NAME>`",
                    parse_mode=ParseMode.MARKDOWN_V2
                ),
                thumbnail_url="https://img.icons8.com/color/96/console.png"
            )
        ]
        await update.inline_query.answer(results, cache_time=300)
        return

    parts = query.split()
    url = parts[0]
    image_name = parts[1] if len(parts) > 1 else ""

    if not is_valid_url(url):
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="⚠️ Invalid URL Format",
                description="Please provide a valid HTTP/HTTPS URL",
                input_message_content=InputTextMessageContent(
                    "⚠️ *Invalid URL Format*\n\nPlease verify the URL and try again\\.",
                    parse_mode=ParseMode.MARKDOWN_V2
                ),
                thumbnail_url="https://img.icons8.com/color/96/error.png"
            )
        ]
        await update.inline_query.answer(results, cache_time=0)
        return

    if image_name and image_name not in SUPPORTED_IMAGES:
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"❌ Unsupported Image: {image_name}",
                description="View list of supported image types",
                input_message_content=InputTextMessageContent(
                    f"❌ *Unsupported Image Type*\n\n"
                    f"📂 *Requested:* `{escape_markdown(image_name)}`\n\n"
                    f"*Supported Image Types:*\n" + 
                    "\n".join([f"• `{escape_markdown(img)}`" for img in sorted(SUPPORTED_IMAGES)]),
                    parse_mode=ParseMode.MARKDOWN_V2
                ),
                thumbnail_url="https://img.icons8.com/color/96/cancel.png"
            )
        ]
        await update.inline_query.answer(results, cache_time=0)
        return

    if image_name in SUPPORTED_IMAGES:
        api_data = await fetch_extraction_data(url, image_name)
        
        if api_data and api_data.get("status") in ["cached", "completed"]:
            download_url = api_data.get("download_url")
            filename = api_data.get("filename", image_name)
            duration = str(api_data.get("duration_seconds", "0"))
            status_text = "Retrieved from cache" if api_data.get("status") == "cached" else "Extraction completed"
            
            keyboard = [[InlineKeyboardButton("📥 Download File", url=download_url)]]

            content = (
                f"✅ *Extraction Successful*\n\n"
                f"📂 *Filename:* `{escape_markdown(filename)}`\n"
                f"🔗 *Filename extracted from:* [URL]({escape_markdown(url)})\n"
                f"⏱ *Processing Time:* `{escape_markdown(duration)}s`\n"
                f"📊 *Status:* {escape_markdown(status_text)}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔧 *FCE Tool:* [Open Source Code]({escape_markdown(GITHUB_URL)})\n"
                f"👤 *by:* [offici5l]({escape_markdown(CHANNEL_URL)})"
            )

            results = [
                InlineQueryResultArticle(
                    id=hashlib.md5(f"{url}{image_name}".encode()).hexdigest(),
                    title=f"✅ Extract {image_name}",
                    description=f"{status_text} • Processing: {duration}s",
                    input_message_content=InputTextMessageContent(
                        content,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    thumbnail_url="https://img.icons8.com/color/96/download--v1.png"
                )
            ]
        elif api_data and api_data.get("status") == "failed":
            error_msg = api_data.get("message", "Unknown error occurred")
            
            keyboard = [
                [InlineKeyboardButton("🌐 Try Web Interface", url=WEB_URL)],
                [InlineKeyboardButton("📱 Get Support", url=CHANNEL_URL)]
            ]
            
            results = [
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"❌ Extraction Failed: {image_name}",
                    description=f"{error_msg[:80]}",
                    input_message_content=InputTextMessageContent(
                        f"❌ *Extraction Failed*\n\n"
                        f"📂 *Requested File:* `{escape_markdown(image_name)}`\n"
                        f"⚠️ *Error Details:* {escape_markdown(error_msg)}\n\n"
                        f"💡 *Suggestion:* This image may not exist in the specified ROM\\. Please verify the image name and try again\\.\n\n"
                        f"🔧 *Alternative:* Try using the [Web Interface]({escape_markdown(WEB_URL)}) for more options\\.",
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    thumbnail_url="https://img.icons8.com/color/96/delete-file.png"
                )
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🌐 Use Web Interface", url=WEB_URL)],
                [InlineKeyboardButton("📱 Contact Support", url=CHANNEL_URL)]
            ]
            
            results = [
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="⚠️ Processing Error",
                    description="Unable to process request. Try web interface.",
                    input_message_content=InputTextMessageContent(
                        f"⚠️ *Request Processing Error*\n\n"
                        f"The extraction service encountered an issue\\. Please try again or use the web interface\\.\n\n"
                        f"🌐 [Open Web Interface]({escape_markdown(WEB_URL)})",
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    thumbnail_url="https://img.icons8.com/color/96/high-priority.png"
                )
            ]
    else:
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"⏳ Awaiting Image Name...",
                description="Continue typing the image name (e.g., boot.img)",
                input_message_content=InputTextMessageContent(
                    "⌨️ *Input Required*\n\nPlease specify the image name you wish to extract\\.\n\n*Example:* boot\\.img",
                    parse_mode=ParseMode.MARKDOWN_V2
                ),
                thumbnail_url="https://img.icons8.com/color/96/typing.png"
            )
        ]

    await update.inline_query.answer(results, cache_time=5)

def main():
    threading.Thread(target=start_fake_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(InlineQueryHandler(inline_query))
    print("FCE Tool Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
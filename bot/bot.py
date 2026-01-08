import os
import re
import threading
import uuid
import httpx
import asyncio
from flask import Flask
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, InlineQueryHandler, ChosenInlineResultHandler, ContextTypes, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")
API_URL = "https://offici5l-fcetool.hf.space/extract"
SUPPORTED_TARGETS = {
    "boot.img", "init_boot.img", "dtbo.img", "super_empty.img",
    "vbmeta.img", "vendor_boot.img", "vendor_kernel_boot.img",
    "preloader.img", "recovery.img", "logo.img"
}

app_server = Flask(__name__)

@app_server.route('/', methods=['GET', 'HEAD'])
def home(): 
    return "Bot is running...", 200

@app_server.route('/health', methods=['GET', 'HEAD'])
def health():
    return "OK", 200

def run_server():
    app_server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def validate_url(url: str) -> bool:
    return bool(re.match(r'^https?://\S+', url, re.IGNORECASE))

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    if not query:
        return

    parts = query.split()

    if len(parts) == 0:
        return

    if len(parts) == 1:
        url = parts[0]
        if not validate_url(url):
            results = [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="❌ Invalid URL",
                    description="Please add http:// or https:// to the beginning",
                    input_message_content=InputTextMessageContent(
                        f"❌ **Invalid URL Format**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"⚠️ Please use format:\n"
                        f"`https://example.com/file.zip target.img`\n\n"
                        f"📝 Your input: `{url}`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                )
            ]
        else:
            results = [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="⚠️ Missing Target File",
                    description="Please specify target file (e.g., boot.img)",
                    input_message_content=InputTextMessageContent(
                        f"⚠️ **Missing Target File**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📝 Usage: `URL target.img`\n\n"
                        f"✅ Supported targets:\n"
                        f"`{', '.join(sorted(SUPPORTED_TARGETS))}`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                )
            ]
        await update.inline_query.answer(results, cache_time=1)
        return

    url, target = parts[0], parts[1]

    if not validate_url(url):
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="❌ Invalid URL",
                description="Please add http:// or https:// to the beginning",
                input_message_content=InputTextMessageContent(
                    f"❌ **Invalid URL Format**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⚠️ URL must start with http:// or https://\n\n"
                    f"📝 Your input: `{url}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            )
        ]
        await update.inline_query.answer(results, cache_time=1)
        return

    if target not in SUPPORTED_TARGETS:
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"❌ Unsupported Target: {target}",
                description="This target file is not supported",
                input_message_content=InputTextMessageContent(
                    f"❌ **Unsupported Target**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⚠️ `{target}` is not supported\n\n"
                    f"✅ Supported targets:\n"
                    f"`{', '.join(sorted(SUPPORTED_TARGETS))}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            )
        ]
        await update.inline_query.answer(results, cache_time=1)
        return

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⏳ Processing...", callback_data="none")]])

    results = [
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=f"✅ Extract: {target}",
            description=f"Click to start extraction",
            reply_markup=keyboard,
            input_message_content=InputTextMessageContent(
                f"⚙️ **Initializing Extraction...**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🎯 **Target:** `{target}`\n"
                f"⏳ **Status:** `Connecting to server...`",
                parse_mode=ParseMode.MARKDOWN
            )
        )
    ]
    await update.inline_query.answer(results, cache_time=1)


async def start_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    targets_list = ", ".join(sorted(SUPPORTED_TARGETS))
    bot_username = context.bot.username
    
    welcome_text = (
        f"👋 **Welcome to Fcetool Bot!**\n\n"
        f"I can extract specific file (like boot.img) from firmware/ROM (.zip) URLs directly.\n\n"
        f"🛠 **How to use:**\n\n"
        f"1️⃣ **Direct Command:**\n"
        f"`/extract <URL> <TARGET>`\n\n"
        f"2️⃣ **Inline Mode:**\n"
        f"Type in any chat:\n"
        f"`@{bot_username} <URL> <TARGET>`\n\n"
        f"3️⃣ **Web Interface:**\n"
        f"[offici5l.github.io/fcetool](https://offici5l.github.io/fcetool)\n\n"
        f"✅ **Supported Targets:**\n"
        f"`{targets_list}`\n\n"
        f"Open Source: [github](https://github.com/offici5l/fcetool)\n"
        f"By: [offici5l](https://t.me/Offici5l_Channel)"
    )

    await update.message.reply_text(
        text=welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )


async def extract_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            f"⚠️ **Usage:**\n`/extract URL TARGET`\n\n"
            f"✅ **Supported targets:**\n`{', '.join(sorted(SUPPORTED_TARGETS))}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    url = context.args[0]
    target = context.args[1]

    # Validate URL
    if not validate_url(url):
        await update.message.reply_text("❌ Invalid URL. Please start with http:// or https://")
        return

    # Validate Target
    if target not in SUPPORTED_TARGETS:
        await update.message.reply_text(
            f"❌ **Unsupported Target**\n"
            f"⚠️ `{target}` is not supported\n"
            f"✅ **Supported:** `{', '.join(sorted(SUPPORTED_TARGETS))}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Send waiting message
    status_msg = await update.message.reply_text(
        f"⚙️ **Processing...**\n━━━━━━━━━━━━━━━━━━\n🎯 **Target:** `{target}`\n⏳ **Status:** `Connecting to server...`",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(API_URL, json={"url": url, "target": target})

            if response.status_code == 200:
                data = response.json()
                dl_url = data.get("download_url", "#")
                
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download File", url=dl_url)]])

                await status_msg.edit_text(
                    text=(
                        f"✅ **Extraction Completed**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📂 **File:** `{target}`\n"
                        f"⏱ **Time:** `{data.get('duration_seconds', 'N/A')}s`\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"Open source: [fcetool](https://github.com/offici5l/fcetool)\n"
                        f"By: [offici5l](https://t.me/Offici5l_Channel)"
                    ),
                    reply_markup=btn,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            else:
                err = response.json().get("message", "API Error")
                await status_msg.edit_text(
                    f"❌ **Failed**\n━━━━━━━━━━━━━━━━━━\n⚠️ **Error:** `{err}`",
                    parse_mode=ParseMode.MARKDOWN
                )

    except Exception as e:
        await status_msg.edit_text(
            f"❌ **Error Occurred**\n━━━━━━━━━━━━━━━━━━\n⚠️ `{str(e)}`",
            parse_mode=ParseMode.MARKDOWN
        )


async def chosen_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chosen_inline_result
    inline_id = result.inline_message_id

    if not inline_id:
        return

    parts = result.query.split()
    if len(parts) < 2:
        return

    url, target = parts[0], parts[1]

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            await context.bot.edit_message_text(
                inline_message_id=inline_id,
                text=f"⚙️ **Processing...**\n━━━━━━━━━━━━━━━━━━\n🎯 Target: `{target}`\n⏳ Status: `Running extraction...`",
                parse_mode=ParseMode.MARKDOWN
            )

            response = await client.post(API_URL, json={"url": url, "target": target})

            if response.status_code == 200:
                data = response.json()
                dl_url = data.get("download_url", "#")

                btn = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download File", url=dl_url)]])

                await context.bot.edit_message_text(
                    inline_message_id=inline_id,
                    text=(
                        f"✅ **Extraction Completed**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📂 **File:** `{target}` extracted from [URL]({url})\n"
                        f"⏱ **Time:** `{data.get('duration_seconds', 'N/A')}s`\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"Open source: [fcetool](https://github.com/offici5l/fcetool)\n"
                        f"By: [offici5l](https://t.me/Offici5l_Channel)"
                    ),
                    reply_markup=btn,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
            else:
                err = response.json().get("message", "API Error")
                await context.bot.edit_message_text(
                    inline_message_id=inline_id,
                    text=f"❌ **Failed**\n━━━━━━━━━━━━━━━━━━\n⚠️ Error: `{err}`",
                    parse_mode=ParseMode.MARKDOWN
                )
    except Exception as e:
        try:
            await context.bot.edit_message_text(
                inline_message_id=inline_id,
                text=(
                    f"❌ **Error Occurred**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⚠️ `{str(e)}`\n\n"
                    f"🌐 **Alternative:**\n"
                    f"Try the [Web Interface](https://offici5l.github.io/fcetool)"
                ),
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False
            )
        except:
            pass

async def main_async():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_help_command))

    app.add_handler(CommandHandler("help", start_help_command))

    app.add_handler(CommandHandler("extract", extract_command))

    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(ChosenInlineResultHandler(chosen_result))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait()

def main():
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
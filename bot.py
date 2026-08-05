import os
import json
import requests
import re
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

TOKEN = os.environ["TOKEN"]
OWNER_ID = 8232776469

DATA_FILE = "links.json"
PARSED_SCRIPTS_FILE = "parsed_scripts.json"

DEFAULT_TEXT = "Превет! Этот бот для получения script с канала Mr.Script"
CHANNEL_USERNAME = "@MrScript09"
CHANNEL_USERNAME2 = "@MrScriptchat"
SOURCE_CHANNEL = "@+YHEA_N06lwMzNDli"  # Новый канал для парсинга

MAX_TEXT_LENGTH = 3000


def load_links():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_links(links):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


def load_parsed_scripts():
    if os.path.exists(PARSED_SCRIPTS_FILE):
        with open(PARSED_SCRIPTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_parsed_scripts(scripts):
    with open(PARSED_SCRIPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(scripts, f, ensure_ascii=False, indent=2)


def fetch_text_from_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Сначала ищем именно блок кода (pre / code / textarea),
        # в котором встречается ключевое слово loadstring
        for tag_name in ["textarea", "pre", "code"]:
            for tag in soup.find_all(tag_name):
                block_text = tag.get_text()
                if "loadstring" in block_text.lower():
                    return block_text.strip()

        # Если такого блока не нашли - ищем построчно среди всего текста
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for line in lines:
            if "loadstring" in line.lower():
                return line

        return "На странице не найден текст с 'loadstring'."
    except Exception as e:
        return f"Ошибка при загрузке страницы: {e}"


async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        member2 = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME2, user_id=user_id)
        return member.status not in ["left", "kicked"] and member2.status not in ["left", "kicked"]
    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        subscribed = await is_subscribed(user_id, context)
    except Exception as e:
        await update.message.reply_text(f"ОШИБКА ПРОВЕРКИ: {e}")
        return

    if not subscribed:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Подписаться на Mr.Script", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton("💬 Подписаться на Mr.Script Chat", url=f"https://t.me/{CHANNEL_USERNAME2.lstrip('@')}")],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]
        ])
        await update.message.reply_text(
            "❌ Вы не подписаны на наши каналы!\n\n"
            "Подпишитесь на оба канала и нажмите кнопку проверки:",
            reply_markup=keyboard
        )
        return
    
    links = load_links()
    if context.args:
        code = context.args[0]
        entry = links.get(code)

        if entry is None:
            await update.message.reply_text(DEFAULT_TEXT)
            return

        if entry["type"] == "text":
            formatted = f"```\n{entry['value']}\n```"
            await update.message.reply_text(formatted, parse_mode="Markdown")
        elif entry["type"] == "url":
            text = fetch_text_from_url(entry["value"])
            await update.message.reply_text(text)
    else:
        await update.message.reply_text(DEFAULT_TEXT)


async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    try:
        subscribed = await is_subscribed(user_id, context)
    except Exception as e:
        await query.edit_message_text(f"ОШИБКА ПРОВЕРКИ: {e}")
        return
    
    if subscribed:
        await query.edit_message_text("✅ Подписка подтверждена! Теперь вы можете использовать бота.\nНажмите /start")
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Подписаться на Mr.Script", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton("💬 Подписаться на Mr.Script Chat", url=f"https://t.me/{CHANNEL_USERNAME2.lstrip('@')}")],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]
        ])
        await query.edit_message_text(
            "❌ Вы всё ещё не подписаны на оба канала!\n\n"
            "Подпишитесь и нажмите кнопку проверки:",
            reply_markup=keyboard
        )


async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /add код текст\nПример: /add site1 Привет, это текст"
        )
        return

    code = context.args[0]
    text = " ".join(context.args[1:])

    links = load_links()
    links[code] = {"type": "text", "value": text}
    save_links(links)

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={code}"

    await update.message.reply_text(
        f"Готово! Код '{code}' сохранён (текст).\nСсылка:\n{link}"
    )


async def add_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /addurl код ссылка_на_сайт\n"
            "Пример: /addurl site1 https://example.com/page"
        )
        return

    code = context.args[0]
    url = context.args[1]

    links = load_links()
    links[code] = {"type": "url", "value": url}
    save_links(links)

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={code}"

    await update.message.reply_text(
        f"Готово! Код '{code}' сохранён (сайт).\n"
        f"Бот будет брать текст с: {url}\n"
        f"Ссылка:\n{link}"
    )


async def parse_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Автоматический парсинг скриптов из канала и создание ссылок"""
    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text("🔄 Начинаю парсинг канала...")
    
    try:
        # Получаем последние сообщения из канала
        messages = []
        async for message in context.bot.get_chat_history(chat_id=SOURCE_CHANNEL, limit=50):
            if message.text:
                messages.append(message)
        
        parsed_scripts = load_parsed_scripts()
        links = load_links()
        new_scripts_count = 0
        
        for msg in messages:
            text = msg.text
            
            # Ищем loadstring в тексте
            if "loadstring" in text.lower():
                # Извлекаем код из сообщения
                code_pattern = r'loadstring\(.*?\)'
                matches = re.findall(code_pattern, text, re.IGNORECASE)
                
                if matches:
                    # Генерируем уникальный код на основе ID сообщения
                    script_code = f"script_{msg.message_id}"
                    
                    # Проверяем, не сохранён ли уже этот скрипт
                    if script_code not in parsed_scripts:
                        # Сохраняем скрипт
                        full_script = text.strip()
                        parsed_scripts[script_code] = {
                            "message_id": msg.message_id,
                            "date": str(msg.date),
                            "script": full_script
                        }
                        
                        # Добавляем в основное хранилище ссылок
                        links[script_code] = {"type": "text", "value": full_script}
                        new_scripts_count += 1
        
        # Сохраняем изменения
        save_parsed_scripts(parsed_scripts)
        save_links(links)
        
        bot_username = (await context.bot.get_me()).username
        
        # Формируем список новых скриптов
        if new_scripts_count > 0:
            response = f"✅ Найдено и сохранено {new_scripts_count} новых скриптов!\n\n"
            response += "📌 Вот ссылки на новые скрипты:\n"
            
            for script_code in list(parsed_scripts.keys())[-new_scripts_count:]:
                link = f"https://t.me/{bot_username}?start={script_code}"
                response += f"\n🔗 {script_code}: {link}"
            
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("ℹ️ Новых скриптов не найдено.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при парсинге: {e}")


async def list_parsed_scripts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все автоматически сохранённые скрипты"""
    if update.effective_user.id != OWNER_ID:
        return

    parsed_scripts = load_parsed_scripts()
    if not parsed_scripts:
        await update.message.reply_text("ℹ️ Автоматически сохранённых скриптов нет.")
        return
    
    bot_username = (await context.bot.get_me()).username
    response = f"📚 Всего автоматически сохранённых скриптов: {len(parsed_scripts)}\n\n"
    
    for i, (code, data) in enumerate(list(parsed_scripts.items())[:20], 1):
        link = f"https://t.me/{bot_username}?start={code}"
        preview = data.get('script', '')[:50] + "..."
        response += f"{i}. {code}\n   📅 {data.get('date', 'Unknown')}\n   {preview}\n   {link}\n\n"
    
    if len(parsed_scripts) > 20:
        response += f"... и ещё {len(parsed_scripts) - 20} скриптов"
    
    await update.message.reply_text(response)


async def delete_parsed_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить автоматически сохранённый скрипт"""
    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) < 1:
        await update.message.reply_text("Использование: /delparsed код_скрипта")
        return
    
    code = context.args[0]
    parsed_scripts = load_parsed_scripts()
    links = load_links()
    
    if code in parsed_scripts:
        del parsed_scripts[code]
        if code in links:
            del links[code]
        
        save_parsed_scripts(parsed_scripts)
        save_links(links)
        await update.message.reply_text(f"✅ Скрипт '{code}' удалён.")
    else:
        await update.message.reply_text(f"❌ Скрипт '{code}' не найден.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text(
        "🤖 Команды управления:\n\n"
        "📝 Ручное управление:\n"
        "/add код текст — сохранить готовый текст под кодом\n"
        "/addurl код ссылка — бот будет брать текст с сайта каждый раз\n"
        "/list — показать все ссылки\n"
        "/delete код — удалить ссылку\n\n"
        "🤖 Автоматический парсинг:\n"
        "/parse — автоматически собрать скрипты из канала\n"
        "/parsed — показать все автоматически собранные скрипты\n"
        "/delparsed код — удалить автоматически собранный скрипт\n\n"
        "/help — это сообщение"
    )


def main():
    app = Application.builder().token(TOKEN).build()
    
    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_link))
    app.add_handler(CommandHandler("addurl", add_url))
    app.add_handler(CommandHandler("list", list_links))
    app.add_handler(CommandHandler("delete", delete_link))
    app.add_handler(CommandHandler("help", help_command))
    
    # Команды для автоматического парсинга
    app.add_handler(CommandHandler("parse", parse_channel))
    app.add_handler(CommandHandler("parsed", list_parsed_scripts))
    app.add_handler(CommandHandler("delparsed", delete_parsed_script))
    
    # Обработчик callback-запросов (кнопки)
    app.add_handler(CallbackQueryHandler(check_subscription, pattern="check_subscription"))
    
    app.run_polling()


if __name__ == "__main__":
    main()

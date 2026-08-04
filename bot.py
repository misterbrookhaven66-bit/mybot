import os
import json
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ["TOKEN"]
OWNER_ID = 8232776469

DATA_FILE = "links.json"

DEFAULT_TEXT = "Превет! Этот бот для получения script с канала Mr.Script"

MAX_TEXT_LENGTH = 3000


def load_links():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_links(links):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    links = load_links()
    if context.args:
        code = context.args[0]
        entry = links.get(code)

        if entry is None:
            await update.message.reply_text(DEFAULT_TEXT)
            return

        if entry["type"] == "text":
            await update.message.reply_text(entry["value"])
        elif entry["type"] == "url":
            text = fetch_text_from_url(entry["value"])
            await update.message.reply_text(text)
    else:
        await update.message.reply_text(DEFAULT_TEXT)


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


async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    links = load_links()
    if not links:
        await update.message.reply_text("Пока нет ни одной ссылки.")
        return

    bot_username = (await context.bot.get_me()).username
    lines = []
    for code, entry in links.items():
        link = f"https://t.me/{bot_username}?start={code}"
        kind = "текст" if entry["type"] == "text" else "сайт"
        preview = entry["value"]
        if len(preview) > 50:
            preview = preview[:50] + "..."
        lines.append(f"{code} ({kind}) → {preview}\n{link}")

    await update.message.reply_text("\n\n".join(lines))


async def delete_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) < 1:
        await update.message.reply_text("Использование: /delete код")
        return

    code = context.args[0]
    links = load_links()
    if code in links:
        del links[code]
        save_links(links)
        await update.message.reply_text(f"Код '{code}' удалён.")
    else:
        await update.message.reply_text(f"Код '{code}' не найден.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text(
        "Команды управления:\n"
        "/add код текст — сохранить готовый текст под кодом\n"
        "/addurl код ссылка — бот будет брать текст с сайта каждый раз\n"
        "/list — показать все ссылки\n"
        "/delete код — удалить ссылку\n"
        "/help — это сообщение"
    )


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_link))
    app.add_handler(CommandHandler("addurl", add_url))
    app.add_handler(CommandHandler("list", list_links))
    app.add_handler(CommandHandler("delete", delete_link))
    app.add_handler(CommandHandler("help", help_command))
    app.run_polling()


if __name__ == "__main__":
    main()

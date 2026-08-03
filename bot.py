import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ["TOKEN"]
OWNER_ID = 8232776469

DATA_FILE = "links.json"

DEFAULT_TEXT = "Превет! Этот бот для получение script с тгк Mrscript права принадлежат им же"


def load_links():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_links(links):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    links = load_links()
    if context.args:
        code = context.args[0]
        text = links.get(code, DEFAULT_TEXT)
        await update.message.reply_text(text)
    else:
        await update.message.reply_text(DEFAULT_TEXT)


async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /add код текст\nПример: /add site1 Привет, это текст с сайта"
        )
        return

    code = context.args[0]
    text = " ".join(context.args[1:])

    links = load_links()
    links[code] = text
    save_links(links)

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={code}"

    await update.message.reply_text(
        f"Готово! Код '{code}' сохранён.\nСсылка:\n{link}"
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
    for code, text in links.items():
        link = f"https://t.me/{bot_username}?start={code}"
        preview = text if len(text) <= 50 else text[:50] + "..."
        lines.append(f"{code} → {preview}\n{link}")

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
        "/add код текст — добавить новую ссылку\n"
        "/list — показать все ссылки\n"
        "/delete код — удалить ссылку\n"
        "/help — это сообщение"
    )


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_link))
    app.add_handler(CommandHandler("list", list_links))
    app.add_handler(CommandHandler("delete", delete_link))
    app.add_handler(CommandHandler("help", help_command))
    app.run_polling()


if __name__ == "__main__":
    main()

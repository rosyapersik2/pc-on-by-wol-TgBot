import os
import json
import socket
from telegram import ReplyKeyboardMarkup
from telegram.ext import (
    Updater, MessageHandler, Filters, ConversationHandler
)

# === CONFIG ===
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1482232013"))

MAC, IP, PORT = range(3)


# === CONFIG STORAGE ===
def load_config(user_id):
    path = f"configs/{user_id}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


def save_config(user_id, data):
    os.makedirs("configs", exist_ok=True)
    with open(f"configs/{user_id}.json", "w") as f:
        json.dump(data, f)


# === KEYBOARDS ===
def main_menu(is_admin=False):
    buttons = [
        ["🔧 Настроить ПК", "⚡ Включить ПК"],
        ["ℹ️ Помощь"]
    ]
    if is_admin:
        buttons.append(["📄 Логи"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def setup_menu():
    return ReplyKeyboardMarkup(
        [
            ["Ввести MAC", "Ввести IP"],
            ["Ввести порт", "Готово"],
            ["Назад"]
        ],
        resize_keyboard=True
    )


# === START ===
def start(update, context):
    user_id = update.effective_user.id
    update.message.reply_text(
        "Главное меню:",
        reply_markup=main_menu(is_admin=(user_id == ADMIN_ID))
    )


# === SETUP FLOW ===
def setup_start(update, context):
    update.message.reply_text("Выберите параметр:", reply_markup=setup_menu())
    return MAC


def setup_router(update, context):
    text = update.message.text

    if text == "Ввести MAC":
        update.message.reply_text("Введите MAC-адрес:")
        return MAC

    if text == "Ввести IP":
        update.message.reply_text("Введите внешний IP или DDNS:")
        return IP

    if text == "Ввести порт":
        update.message.reply_text("Введите порт (обычно 9):")
        return PORT

    if text == "Готово":
        user_id = update.effective_user.id
        save_config(user_id, context.user_data)
        update.message.reply_text(
            "Настройки сохранены!",
            reply_markup=main_menu(is_admin=(user_id == ADMIN_ID))
        )
        return ConversationHandler.END

    if text == "Назад":
        update.message.reply_text(
            "Главное меню:",
            reply_markup=main_menu(is_admin=(update.effective_user.id == ADMIN_ID))
        )
        return ConversationHandler.END

    update.message.reply_text("Неизвестная команда.")
    return MAC


def set_mac(update, context):
    context.user_data["mac"] = update.message.text
    update.message.reply_text("MAC сохранён.", reply_markup=setup_menu())
    return MAC


def set_ip(update, context):
    context.user_data["ip"] = update.message.text
    update.message.reply_text("IP сохранён.", reply_markup=setup_menu())
    return MAC


def set_port(update, context):
    try:
        context.user_data["port"] = int(update.message.text)
        update.message.reply_text("Порт сохранён.", reply_markup=setup_menu())
    except:
        update.message.reply_text("Некорректный порт. Попробуйте снова.")
    return MAC


# === WOL ===
def send_magic_packet(mac, ip, port):
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    packet = b"\xff" * 6 + mac_bytes * 16
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (ip, port))


def wake(update, context):
    user_id = update.effective_user.id
    cfg = load_config(user_id)

    if not cfg:
        update.message.reply_text("Сначала настройте ПК через '🔧 Настроить ПК'")
        return

    try:
        send_magic_packet(cfg["mac"], cfg["ip"], cfg["port"])
        update.message.reply_text("ПК включается!")
    except Exception as e:
        log_error(f"Wake error for {user_id}: {e}")
        update.message.reply_text("Ошибка при отправке WoL.")


# === LOGS ===
def log_error(text):
    with open("bot.log", "a") as f:
        f.write(text + "\n")


def logs(update, context):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("У вас нет доступа.")
        return
if not os.path.exists("bot.log"):
        update.message.reply_text("Логи пусты.")
        return

    with open("bot.log", "r") as f:
        text = f.read()[-4000:]

    update.message.reply_text(text or "Логи пусты.")


# === HELP ===
def help_message():
    return (
        "📘 *Расширенная помощь по Wake-on-LAN*\n\n"
        "🔧 *1. BIOS*\n"
        "• Включите Wake on LAN\n"
        "• Power On By PCI-E / PME — включить\n"
        "• Fast Boot — выключить\n"
        "• Разрешить питание на сетевую карту в S5\n\n"
        "🪟 *2. Windows*\n"
        "• В драйвере сетевой карты включить WoL\n"
        "• Разрешить устройству выводить ПК из сна\n"
        "• Отключить «Разрешить отключение устройства для экономии энергии»\n"
        "• Проверить, что ПК выключается в S5, а не в гибернацию\n\n"
        "📡 *3. Роутер*\n"
        "• Закрепить IP (DHCP Reservation)\n"
        "• Привязать MAC → IP (ARP Binding)\n"
        "• Пробросить UDP 9\n"
        "• Отключить NAT Boost / Hardware NAT, если WoL нестабилен\n\n"
        "🧪 *4. Проверка*\n"
        "• Сначала протестировать WoL внутри сети\n"
        "• Потом через интернет\n"
        "• Потом через Telegram‑бота\n\n"
        "❗ *5. Частые проблемы*\n"
        "• ПК включается только из сна — включите PME\n"
        "• WoL работает 5–30 минут — включите ARP Binding\n"
        "• Ошибка 4937 — неверный IP в пробросе порта\n"
        "• Провайдер режет UDP — используйте VPN или другой порт\n"
    )


def help_handler(update, context):
    update.message.reply_text(help_message(), parse_mode="Markdown")


# === ROUTER ===
def router(update, context):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🔧 Настроить ПК":
        return setup_start(update, context)

    if text == "⚡ Включить ПК":
        return wake(update, context)

    if text == "ℹ️ Помощь":
        return help_handler(update, context)

    if text == "📄 Логи":
        return logs(update, context)

    update.message.reply_text(
        "Неизвестная команда.",
        reply_markup=main_menu(is_admin=(user_id == ADMIN_ID))
    )


# === MAIN ===
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    setup_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("🔧 Настроить ПК"), setup_start)],
        states={
            MAC: [
                MessageHandler(Filters.regex("Ввести MAC"), setup_router),
                MessageHandler(Filters.regex("Ввести IP"), setup_router),
                MessageHandler(Filters.regex("Ввести порт"), setup_router),
                MessageHandler(Filters.regex("Готово"), setup_router),
                MessageHandler(Filters.regex("Назад"), setup_router),
                MessageHandler(Filters.text & ~Filters.command, set_mac),
            ],
            IP: [MessageHandler(Filters.text & ~Filters.command, set_ip)],
            PORT: [MessageHandler(Filters.text & ~Filters.command, set_port)],
        },
        fallbacks=[MessageHandler(Filters.regex("Назад"), setup_router)],
    )

    dp.add_handler(setup_handler)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, router))

    updater.start_polling()
    updater.idle()


if name == "main":
    main()
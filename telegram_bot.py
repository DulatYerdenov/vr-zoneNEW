import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    ContentType,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VRZoneClientBot")

# Загрузка переменных
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_CHAT_ID_STR = os.getenv("ADMIN_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")
if not ADMIN_BOT_TOKEN:
    raise ValueError("ADMIN_BOT_TOKEN не задан в .env (токен админ-бота)")
if not ADMIN_CHAT_ID_STR:
    raise ValueError("ADMIN_CHAT_ID не задан в .env")

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_STR.strip())
except ValueError:
    raise ValueError(f"ADMIN_CHAT_ID должен быть числом! Получено: '{ADMIN_CHAT_ID_STR}'")

logger.info(f"ADMIN_CHAT_ID = {ADMIN_CHAT_ID}")

# Клиентский бот
client_bot = Bot(token=BOT_TOKEN)

# Отдельный бот для отправки админу (VR_Admin)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)

dp = Dispatcher()


# Клавиатура "Поделиться номером"
share_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="📱 Поделиться номером для уведомлений",
                request_contact=True
            )
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Нажмите кнопку ниже ↓"
)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    await message.answer(
        "Привет! 👋\n"
        "Я бот VR Zone.\n"
        "Чтобы получать уведомления о бронировании в личные сообщения,\n"
        "поделитесь своим номером телефона:",
        reply_markup=share_kb
    )

    # Отправляем админу
    await _notify_admin(
        f"Новый клиент начал общение:\n"
        f"Имя: {user.full_name}\n"
        f"Username: @{user.username or 'нет'}\n"
        f"User ID: {user.id}"
    )


@dp.message(F.content_type == ContentType.CONTACT)
async def handle_contact(message: Message):
    contact = message.contact
    if not contact or not contact.phone_number:
        await message.answer("Не удалось получить контакт. Попробуйте ещё раз.")
        return

    phone = contact.phone_number.strip()
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Клиент"

    await message.answer(
        f"Спасибо, {first_name}! ✅\n"
        f"Ваш номер {phone} сохранён.\n"
        "Теперь уведомления о записях будут приходить сюда.",
        reply_markup=ReplyKeyboardRemove()
    )

    # Отправляем админу
    await _notify_admin(
        f"Новый клиент поделился номером!\n"
        f"Имя: {first_name}\n"
        f"Телефон: {phone}\n"
        f"User ID: {user_id}\n"
        f"Username: @{message.from_user.username or 'нет'}"
    )


@dp.message()
async def forward_all(message: Message):
    if message.chat.type == "private":
        await _forward_to_admin(message)


async def _forward_to_admin(message: Message):
    try:
        text = f"Сообщение от клиента @{message.from_user.username or 'нет'} (ID: {message.from_user.id})\n"

        if message.text:
            text += f"Текст: {message.text}"
        elif message.contact:
            text += f"Контакт: {message.contact.phone_number} ({message.contact.first_name})"

        await admin_bot.send_message(ADMIN_CHAT_ID, text)
        logger.info("Сообщение переслано админу")
    except Exception as e:
        logger.error(f"Ошибка пересылки админу: {e}")


async def _notify_admin(text: str):
    try:
        await admin_bot.send_message(ADMIN_CHAT_ID, text)
        logger.info("Уведомление отправлено админу")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления админу: {e}")


async def main():
    logger.info("Клиентский бот VR_ZONA запущен")
    await dp.start_polling(client_bot)


if __name__ == "__main__":
    asyncio.run(main())
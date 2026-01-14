import os
import logging
import re
import requests
from datetime import datetime
from typing import Optional, Tuple

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# ENV
# =========================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN или CHAT_ID не заданы в .env")

# Валидация CHAT_ID
try:
    CHAT_ID = int(CHAT_ID)
except ValueError:
    raise RuntimeError(f"CHAT_ID должен быть числом, получено: {CHAT_ID}")

# =========================
# Flask
# =========================
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bookings.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# Database
# =========================
class Client(db.Model):
    """Модель клиента"""
    __tablename__ = "client"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=True)
    first_booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связь с бронированиями
    bookings = db.relationship("Booking", backref="client", lazy=True)
    
    def __repr__(self):
        return f"<Client {self.name}>"


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=True)  # nullable для старых данных
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    
    # Миграция: добавить client_id колонку если её нет
    import sqlite3
    db_path = os.path.join(app.instance_path, "bookings.db")
    
    # Проверяем, есть ли файл БД
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Проверяем, есть ли колонка client_id в таблице booking
            cur.execute("PRAGMA table_info(booking)")
            columns = [col[1] for col in cur.fetchall()]
            
            if "client_id" not in columns:
                logger.info("⚠️ Миграция: добавляем client_id в таблицу booking...")
                cur.execute("""
                    ALTER TABLE booking 
                    ADD COLUMN client_id INTEGER DEFAULT NULL
                """)
                conn.commit()
                logger.info("✅ Миграция завершена: client_id добавлен")
            
            conn.close()
        except Exception as e:
            logger.error(f"❌ Ошибка миграции БД: {e}")

# =========================
# Telegram Notifications (Simple HTTP)
# =========================
def send_telegram_message(text: str) -> None:
    """Отправка уведомления администратору через Telegram (синхронно)"""
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("⚠️ BOT_TOKEN или CHAT_ID не установлены")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data, timeout=5)
        if response.status_code == 200:
            logger.info("✅ Уведомление отправлено в Telegram")
        else:
            logger.error(f"❌ Telegram ошибка: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки Telegram: {e}")

# =========================
# Validation Functions
# =========================
def validate_phone(phone: str) -> bool:
    """Проверка корректности телефона"""
    # Простая проверка: минимум 10 цифр
    digits = re.sub(r'\D', '', phone)
    return len(digits) >= 10


def validate_booking_data(name: str, phone: str, date: str, time_: str) -> Tuple[bool, str]:
    """Валидация данных бронирования"""
    if not all([name, phone, date, time_]):
        return False, "Заполните все обязательные поля!"
    
    if len(name.strip()) < 2:
        return False, "Имя должно быть минимум 2 символа"
    
    if not validate_phone(phone):
        return False, "Некорректный номер телефона"
    
    return True, ""

# =========================
# Routes
# =========================
@app.route("/")
def index() -> str:
    """Главная страница"""
    return render_template("index.html")


@app.route("/book", methods=["POST"])
def book() -> str:
    """Обработка бронирования"""
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    date = request.form.get("date", "").strip()
    time_ = request.form.get("time", "").strip()
    selection = request.form.get("duration") or request.form.get("game") or "Не выбрано"

    # Валидация
    is_valid, error_msg = validate_booking_data(name, phone, date, time_)
    if not is_valid:
        flash(error_msg, "error")
        return redirect(url_for("index") + "#booking")

    try:
        # Найти или создать клиента
        client = Client.query.filter_by(phone=phone).first()
        if not client:
            client = Client(name=name, phone=phone)
            db.session.add(client)
            db.session.flush()  # Чтобы получить ID
            logger.info(f"✅ Новый клиент: {name} ({phone})")
        else:
            # Обновить имя если оно изменилось
            if client.name != name:
                client.name = name
            logger.info(f"✅ Клиент найден: {name} ({phone})")
        
        # Сохранение бронирования
        booking = Booking(
            client_id=client.id,
            name=name,
            phone=phone,
            date=date,
            time=time_,
            duration=selection
        )
        db.session.add(booking)
        db.session.commit()

        # Отправка в Telegram
        message = (
            f"🚀 <b>Новая запись в VR ZONE</b>\n\n"
            f"👤 <b>Имя:</b> {name}\n"
            f"📞 <b>Телефон:</b> {phone}\n"
            f"📅 <b>Дата:</b> {date}\n"
            f"🕒 <b>Время:</b> {time_}\n"
            f"🎮 <b>Выбор:</b> {selection}\n\n"
            f"⏰ <b>Создано:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        send_telegram_message(message)
        logger.info(f"✅ Бронирование добавлено: {name} ({phone})")
        flash("Вы успешно записались! Мы скоро свяжемся с вами.", "success")
        
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")
        flash("Ошибка при сохранении данных.", "error")

    return redirect(url_for("index") + "#booking")


@app.route("/prices")
def prices() -> str:
    """Страница с ценами"""
    return render_template("prices.html")


@app.route("/games")
def games() -> str:
    """Страница с играми"""
    return render_template("games.html")


@app.route("/about")
def about() -> str:
    """Страница о нас"""
    return render_template("about.html")

# =========================
# Error Handlers
# =========================
@app.errorhandler(404)
def not_found(error) -> Tuple[str, int]:
    """Обработка 404"""
    logger.warning(f"404: {request.path}")
    return render_template("index.html"), 404


@app.errorhandler(500)
def internal_error(error) -> Tuple[str, int]:
    """Обработка 500"""
    logger.error(f"500 Error: {error}")
    db.session.rollback()
    flash("Внутренняя ошибка сервера. Попробуйте позже.", "error")
    return render_template("index.html"), 500


# =========================
# Run
# =========================
if __name__ == "__main__":
    logger.info("🎮 Запуск VR ZONE приложения...")
    app.run(debug=True, port=5000)
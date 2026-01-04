from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from aiogram import Bot
import threading
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vr-zone-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# === Настройки Telegram ===
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

bot = Bot(token=BOT_TOKEN)

# === Модель бронирования ===
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Создаём таблицы при первом запуске
with app.app_context():
    db.create_all()

# === Асинхронная функция отправки сообщения ===
async def send_telegram_async(text):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

# === Обёртка для запуска асинхронной функции в отдельном потоке ===
def send_telegram_message(text):
    # Запускаем асинхронную функцию в новом event loop в отдельном потоке
    threading.Thread(target=lambda: asyncio.run(send_telegram_async(text))).start()

# === Роуты ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/book', methods=['POST'])
def book():
    name = request.form.get('name')
    phone = request.form.get('phone')
    date = request.form.get('date')
    time = request.form.get('time')
    duration = request.form.get('duration')

    if not all([name, phone, date, time, duration]):
        flash('Заполните все поля формы!', 'error')
        return redirect(url_for('index') + '#booking')

    # Сохраняем в базу
    new_booking = Booking(name=name, phone=phone, date=date, time=time, duration=duration)
    db.session.add(new_booking)
    db.session.commit()

    # Красивое сообщение в Telegram
    message = f"""
🚀 <b>Новая запись в VR ZONE!</b>

👤 <b>Имя:</b> {name}
📞 <b>Телефон:</b> {phone}
📅 <b>Дата:</b> {date}
🕐 <b>Время:</b> {time}
🎮 <b>Тариф:</b> {duration}
⏰ <b>Время записи:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""

    # Отправляем в Telegram (асинхронно, не блокирует сайт)
    send_telegram_message(message)

    flash('Вы успешно записались! Мы свяжемся с вами скоро.', 'success')
    return redirect(url_for('index') + '#booking')

# Остальные страницы (если есть)
@app.route('/prices')
def prices():
    return render_template('prices.html')

@app.route('/games')
def games():
    return render_template('games.html')

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    print("🚀 VR ZONE запущен! Перейдите: http://127.0.0.1:5000")
    app.run(debug=True)
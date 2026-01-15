# core.py
import os
import logging
import re
import requests
from typing import Tuple

from flask import Flask, flash, redirect, url_for, request
from models import db


class VRZoneBaseApp:
    """Базовый класс приложения VR Zone"""

    def __init__(self):
        # Flask app
        self.app = Flask(__name__, instance_relative_config=True)

        # 🔹 ЛОГГЕР — СНАЧАЛА!
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        self.logger = logging.getLogger("VRZone")

        # 🔹 Конфигурация из окружения
        self._load_config()

        # 🔹 Flask config
        self.app.config["SECRET_KEY"] = self.secret_key
        self.app.config["SQLALCHEMY_DATABASE_URI"] = (
            "sqlite:///" + os.path.join(self.app.instance_path, "bookings.db")
        )
        self.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        # 🔹 SQLAlchemy
        db.init_app(self.app)

        # 🔹 Создание БД
        self._init_db()

        # 🔹 Ошибки
        self._register_error_handlers()

        self.logger.info("VRZone приложение успешно инициализировано")

    # -------------------------------------------------

    def _load_config(self):
        self.bot_token = os.getenv("BOT_TOKEN")
        self.chat_id = os.getenv("CHAT_ID")
        self.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN не задан в окружении контейнера")

        if not self.chat_id:
            raise RuntimeError("CHAT_ID не задан в окружении контейнера")

        try:
            self.chat_id = int(self.chat_id)
        except ValueError:
            raise RuntimeError("CHAT_ID должен быть числом")

        self.logger.info("Конфигурация загружена (BOT_TOKEN, CHAT_ID)")

    # -------------------------------------------------

    def _init_db(self):
        os.makedirs(self.app.instance_path, exist_ok=True)

        with self.app.app_context():
            db.create_all()
            self.logger.info("База данных инициализирована")

    # -------------------------------------------------

    def _register_error_handlers(self):
        @self.app.errorhandler(404)
        def not_found(error):
            self.logger.warning(f"404: {request.path}")
            return "Страница не найдена", 404

        @self.app.errorhandler(500)
        def internal_error(error):
            self.logger.exception("500 ошибка")
            db.session.rollback()
            flash("Внутренняя ошибка сервера", "error")
            return redirect(url_for("index"))

    # -------------------------------------------------
    # Валидация

    @staticmethod
    def validate_phone(phone: str) -> bool:
        digits = re.sub(r"\D", "", phone)
        return len(digits) >= 10

    @staticmethod
    def validate_booking_data(
        name: str, phone: str, date: str, time_: str
    ) -> Tuple[bool, str]:

        if not all([name.strip(), phone.strip(), date.strip(), time_.strip()]):
            return False, "Заполните все поля"

        if len(name.strip()) < 2:
            return False, "Имя слишком короткое"

        if not VRZoneBaseApp.validate_phone(phone):
            return False, "Неверный номер телефона"

        return True, ""

    # -------------------------------------------------
    # Telegram

    def send_telegram_message(self, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }

        try:
            r = requests.post(url, data=payload, timeout=10)
            if r.ok:
                self.logger.info("Сообщение отправлено в Telegram")
            else:
                self.logger.error(f"Telegram ошибка: {r.status_code} {r.text}")
        except Exception:
            self.logger.exception("Ошибка отправки Telegram")

    # -------------------------------------------------

    def run(self, port: int = 5000, debug: bool = False):
        self.logger.info(f"Flask запущен на порту {port}")
        self.app.run(host="0.0.0.0", port=port, debug=debug)

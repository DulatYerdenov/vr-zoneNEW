# app.py
from core import VRZoneBaseApp
from flask import render_template, request, redirect, url_for, flash
from models import db, Client, Booking
from datetime import datetime
# app.py
from core import VRZoneBaseApp
vr_app = VRZoneBaseApp()
app = vr_app.app

class VRZoneApp(VRZoneBaseApp):
    """Конкретная реализация приложения VR Zone"""

    def __init__(self):
        super().__init__()
        self._register_routes()

    def _register_routes(self):
        @self.app.route("/")
        def index():
            return render_template("index.html")

        @self.app.route("/prices")
        def prices():
            return render_template("prices.html")

        @self.app.route("/games")
        def games():
            return render_template("games.html")

        @self.app.route("/about")
        def about():
            return render_template("about.html")

        @self.app.route("/equipment")
        def equipment():
            return render_template("equipment.html")

        @self.app.route("/book", methods=["POST"])
        def book():
            name    = request.form.get("name", "").strip()
            phone   = request.form.get("phone", "").strip()
            date    = request.form.get("date", "").strip()
            time_   = request.form.get("time", "").strip()
            selection = request.form.get("duration") or request.form.get("game") or "Не выбрано"

            is_valid, msg = self.validate_booking_data(name, phone, date, time_)
            if not is_valid:
                flash(msg, "error")
                return redirect(url_for("index") + "#booking")

            try:
                with self.app.app_context():
                    client = Client.query.filter_by(phone=phone).first()
                    if not client:
                        client = Client(name=name, phone=phone)
                        db.session.add(client)
                        db.session.flush()
                    
                    if client.name != name:
                        client.name = name

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

                # Уведомление админу
                message = (
                    f"🚀 <b>Новая запись VR ZONE</b>\n\n"
                    f"👤 {name}\n"
                    f"📞 {phone}\n"
                    f"📅 {date} в {time_}\n"
                    f"🎮 {selection}\n"
                    f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                )
                self.send_telegram_message(message)

                flash("Запись успешно создана! Скоро с вами свяжутся.", "success")
            
            except Exception as e:
                self.logger.error(f"Ошибка бронирования: {e}")
                flash("Ошибка при сохранении. Попробуйте позже.", "error")

            return redirect(url_for("index") + "#booking")


if __name__ == "__main__":
    application = VRZoneApp()
    application.run(debug=True, port=5000)
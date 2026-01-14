FROM python:3.11-slim

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY . .

# Создаём папку instance для БД
RUN mkdir -p instance

# Expose порт для Flask
EXPOSE 5000

# Запуск приложения
CMD ["python", "app.py"]

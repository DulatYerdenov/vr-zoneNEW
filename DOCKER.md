# Docker запуск приложения VR ZONE

## Требования
- Docker и Docker Compose установлены
- Файл `.env` с переменными `BOT_TOKEN`, `CHAT_ID`, `SECRET_KEY`

## Подготовка

### 1. Убедитесь, что `.env` существует и заполнен
```bash
cat .env
# Должно вывести:
# BOT_TOKEN=ваш token
# CHAT_ID=ваш id 
# SECRET_KEY=...
```

### 2. Собрать образ
```bash
docker build -t vr-zone:latest .
```

### 3. Запустить контейнер через Docker Compose
```bash
docker-compose up -d
```

Приложение будет доступно на `http://localhost:5000`

## Команды

```bash
# Посмотреть логи
docker-compose logs -f vr-zone

# Остановить контейнер
docker-compose down

# Перезапустить
docker-compose restart

# Удалить всё (включая БД)
docker-compose down -v
```

## Как `.env` подхватывается в Docker

1. `docker-compose.yml` содержит `env_file: - .env`
2. Docker Compose читает файл `.env` и передаёт переменные в контейнер
3. `app.py` выполняет `load_dotenv()` и получает `BOT_TOKEN`, `CHAT_ID`, `SECRET_KEY`
4. Переменные становятся доступны через `os.getenv("BOT_TOKEN")` и т.д.

**Важно:** `.env` файл НЕ копируется в образ Docker, он передаётся через runtime переменные окружения в `docker-compose.yml`.

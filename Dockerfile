FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir aiogram==3.7.0
COPY . .
CMD ["python", "bot.py"]

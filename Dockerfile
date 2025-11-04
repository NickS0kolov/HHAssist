FROM python:3.12.12


WORKDIR /app


COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Команда по умолчанию
CMD ["python", "-m", "app.bot"]

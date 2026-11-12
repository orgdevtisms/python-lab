# a imagem oficial já traz Python, Playwright e o Chromium
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8085
CMD ["gunicorn", "-b", "0.0.0.0:8085", "--workers", "2", "--timeout", "240", "app:app"]

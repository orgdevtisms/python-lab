# a imagem oficial já traz Python, Playwright e o Chromium (versão 1.49.0 — igual ao requirements.txt)
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
# mesmo interpretador para instalar e para rodar
RUN python3 -m pip install --no-cache-dir -r requirements.txt \
 && python3 -c "import playwright, flask, PIL; print('playwright OK em', playwright.__file__)"
COPY app.py .
EXPOSE 8085
CMD ["python3", "-m", "gunicorn", "-b", "0.0.0.0:8085", "--workers", "2", "--timeout", "240", "app:app"]


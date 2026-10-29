FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 1000 --create-home memory
COPY app.py memory.py schema.sql ./
USER memory
EXPOSE 8852
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8852/health',timeout=2)"
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8852","--no-access-log"]

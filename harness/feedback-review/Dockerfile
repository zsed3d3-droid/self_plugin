FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 REVIEW_DATA=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 1000 --create-home reviewer && mkdir /data && chown reviewer:reviewer /data
COPY app.py catalog.json ./
COPY static ./static
USER reviewer
EXPOSE 8840
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8840/health',timeout=2)"
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8840","--no-access-log"]

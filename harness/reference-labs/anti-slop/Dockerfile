FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY web ./web
USER 65534:65534
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/after.html',timeout=2)"
CMD ["python","-m","http.server","8080","--bind","0.0.0.0","--directory","web"]

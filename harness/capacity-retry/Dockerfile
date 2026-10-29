FROM python:3.13-alpine
WORKDIR /app
COPY retry_state.py observer.py ./
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 65534:65534
CMD ["python", "observer.py"]

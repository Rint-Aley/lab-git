FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/people.db

WORKDIR /app

# A non-root runtime user keeps the application process unprivileged. Creating
# /data with this ownership lets a fresh named Docker volume remain writable.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app \
    && install --directory --owner=app --group=app /data

COPY --chown=app:app requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app app ./app

USER app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_RETRIES=10 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --prefer-binary -r /app/requirements.txt

COPY . /app

RUN mkdir -p /app/instance /app/static/uploads

EXPOSE 8000

CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:8000", "app:app"]

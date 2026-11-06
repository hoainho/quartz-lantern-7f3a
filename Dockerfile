FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/tmp/articles

WORKDIR /app

# Dependencies first so code changes do not invalidate this layer.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY kbsync ./kbsync
COPY prompts ./prompts
COPY main.py .

RUN useradd --create-home --uid 10001 job
USER job

# Runs once and exits (0 = clean). `docker run -e API_KEY=... <image>` is enough;
# extra args such as `main.py` are ignored.
ENTRYPOINT ["python", "main.py"]

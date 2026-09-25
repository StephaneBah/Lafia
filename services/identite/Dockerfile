FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY pyproject.toml /construction/identite/
COPY src /construction/identite/src
RUN pip install /construction/identite && rm -rf /construction

RUN useradd --system --no-create-home --uid 10001 lafia
USER lafia

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=10s --retries=3 --start-period=10s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/identite/sante', timeout=5)"]
CMD ["uvicorn", "identite.service:app", "--host", "0.0.0.0", "--port", "8000"]

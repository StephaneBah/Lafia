FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# commun entre dans l'image à la construction : aucune dépendance d'exécution entre services.
COPY --from=commun pyproject.toml /construction/commun/
COPY --from=commun src /construction/commun/src
COPY pyproject.toml /construction/soin/
COPY src /construction/soin/src
RUN pip install /construction/commun /construction/soin && rm -rf /construction

RUN useradd --system --no-create-home --uid 10001 lafia
USER lafia

EXPOSE 8000
# Sain quand le service répond. Le noyau a sa propre sonde ; /api/soin/sante rapporte la chaîne entière.
HEALTHCHECK --interval=15s --timeout=10s --retries=3 --start-period=10s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/soin/openapi.json', timeout=5)"]
CMD ["uvicorn", "soin.service:app", "--host", "0.0.0.0", "--port", "8000"]

# Image d'un service Lafia, construite depuis services/ avec les bibliothèques du dépôt en contextes nommés :
#   docker build --build-arg SERVICE=soin --build-context commun=commun --build-context donnees=donnees services
# Les bibliothèques entrent dans l'image à la construction : aucune dépendance d'exécution entre services.
# BIBLIOTHEQUES nomme celles que le service installe : commun pour tous ; identite y ajoute donnees,
# où il lit ses comptes de démonstration. Chacune s'installe depuis ses sources, jamais depuis PyPI.

FROM python:3.11-slim
ARG SERVICE
ARG BIBLIOTHEQUES=commun

ENV SERVICE=${SERVICE} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY --from=commun pyproject.toml /construction/commun/
COPY --from=commun src /construction/commun/src
COPY --from=donnees pyproject.toml /construction/donnees/
COPY --from=donnees src /construction/donnees/src
COPY ${SERVICE}/pyproject.toml /construction/${SERVICE}/
COPY ${SERVICE}/src /construction/${SERVICE}/src
RUN pip install $(for bibliotheque in ${BIBLIOTHEQUES}; do echo /construction/$bibliotheque; done) \
        /construction/${SERVICE} \
    && rm -rf /construction

RUN useradd --system --no-create-home --uid 10001 lafia
USER lafia

EXPOSE 8000
# Sain quand le service répond. Le noyau a sa propre sonde ; /api/<service>/sante rapporte la chaîne entière.
HEALTHCHECK --interval=15s --timeout=10s --retries=3 --start-period=10s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:8000/api/{os.environ[\"SERVICE\"]}/openapi.json', timeout=5)"
CMD exec uvicorn "${SERVICE}.service:app" --host 0.0.0.0 --port 8000

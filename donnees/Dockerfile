# Image du chargement du jeu de démonstration, construite depuis donnees/ avec commun en second contexte :
#   docker build --build-context commun=commun donnees
# Elle écrit le jeu dans le noyau, puis s'arrête.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY --from=commun pyproject.toml /construction/commun/
COPY --from=commun src /construction/commun/src
COPY pyproject.toml /construction/donnees/
COPY src /construction/donnees/src
RUN pip install /construction/commun /construction/donnees && rm -rf /construction

RUN useradd --system --no-create-home --uid 10001 lafia
USER lafia

CMD ["python", "-m", "donnees.chargement"]

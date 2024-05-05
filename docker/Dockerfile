FROM python:3.11

ENV POETRY_HOME=/opt/poetry
RUN python3 -m venv "$POETRY_HOME" \
    && "$POETRY_HOME/bin/pip" install poetry==1.8.2 \
    && ln -s "$POETRY_HOME/bin/poetry" /usr/local/bin/poetry

WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN poetry install --without=dev --no-root --no-directory

COPY . /app
RUN poetry install --without=dev --no-directory

ENTRYPOINT ["/usr/local/bin/poetry", "run", "/app/docker/entrypoint.sh"]

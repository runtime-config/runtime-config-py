ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-buster

ENV POETRY_VERSION=1.1.13

WORKDIR /opt/app/

RUN apt update \
    && apt-get install -y wget \
    && ln -s /root/.poetry/bin/poetry /usr/bin/poetry \
    && wget https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py \
    && python ./get-poetry.py --version $POETRY_VERSION \
    && poetry config virtualenvs.create false \
    && rm ./get-poetry.py \
    && apt-get purge -y wget \
    && apt autoremove -y \
    && apt autoclean -y \
    && rm -fr /var/lib/apt/lists /var/lib/cache/* /var/log/* \
    && touch README.md

COPY pyproject.toml poetry.lock /opt/app/
RUN /bin/bash -c 'mkdir -p src/runtime_config && touch src/runtime_config/__init__.py && poetry install --no-interaction --no-ansi'

COPY src/ /opt/app/src
COPY tests/ /opt/app/tests

ENTRYPOINT ["/usr/local/bin/pytest", "tests"]

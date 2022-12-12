ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-buster

WORKDIR /opt/app/

COPY pyproject.toml requirements.txt /opt/app/
RUN pip install -r requirements.txt

COPY src/ /opt/app/src
COPY tests/ /opt/app/tests

ENTRYPOINT ["/usr/local/bin/pytest", "tests"]

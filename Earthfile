VERSION 0.7
FROM python:3.11-slim-bookworm
WORKDIR /opt/resource

requirements:
  RUN python3 -m pip install poetry
  COPY pyproject.toml .
  COPY poetry.lock .
  RUN poetry export --without-hashes --format=requirements.txt > requirements.txt
  SAVE ARTIFACT requirements.txt

build:
  RUN mkdir -p /opt/resource/
  COPY +requirements/requirements.txt requirements.txt

  RUN python3 -m pip install --upgrade pip && \
      pip install -r requirements.txt --no-deps --no-cache-dir

  WORKDIR /opt/resource/
  COPY concourse.py ./concourse.py
  RUN python3 -m concoursetools . -r concourse.py

  ENTRYPOINT ["python3"]
  SAVE IMAGE mitodl/ol-concourse-github-issues

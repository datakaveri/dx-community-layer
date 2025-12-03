FROM python:3.14.1-alpine3.22 AS builder
ENV USER=devops
RUN apk add --no-cache \
  build-base \
  libpq-dev \
  && adduser -D ${USER} \
  && pip install --no-cache-dir uv
USER ${USER}
WORKDIR /home/${USER}
ENV VIRTUALENV=/home/${USER}/venv
RUN python3 -m venv $VIRTUALENV
ENV PATH="${VIRTUALENV}/bin:$PATH"
COPY --chown=${USER} pyproject.toml poetry.lock README.md ./
COPY --chown=${USER} src/ src/
RUN uv pip install --python=$VIRTUALENV/bin/python .

FROM python:3.13.8-alpine3.22 AS runtime
ENV USER=devops
RUN apk add --no-cache \
  libpq \
  curl \
  netcat-openbsd \
  && adduser -D ${USER}
USER ${USER}
WORKDIR /home/${USER}
COPY --from=builder /home/${USER}/venv /home/${USER}/venv
COPY --from=builder /home/${USER}/src /home/${USER}/src
ENV VIRTUALENV=/home/${USER}/venv
ENV PATH="${VIRTUALENV}/bin:$PATH"
EXPOSE 5000
CMD [ "server" ]

FROM debian:stable
SHELL ["/bin/bash", "-c"]
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# この二行をまとめたいが、何故かこう書かないととコケる……
RUN apt-get update && apt-get install -y curl
RUN apt-get install -y --no-install-recommends build-essential

RUN curl -Lf https://rye.astral.sh/get | RYE_NO_AUTO_INSTALL=1 RYE_INSTALL_OPTION="--yes" bash && \
    echo 'source "/root/.rye/env"' >> ~/.bashrc

WORKDIR /bot
COPY .python-version pyproject.toml requirements.lock requirements-dev.lock .env /bot/

RUN source ~/.bashrc && rye sync --no-lock

COPY src /bot/

EXPOSE 3000
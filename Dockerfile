FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e .

COPY sample_repo/ sample_repo/

# Give git_status() a real repository to inspect inside the image.
RUN git config --global user.email "agent@localhost" \
    && git config --global user.name "Repository Agent" \
    && git init sample_repo \
    && git -C sample_repo add . \
    && git -C sample_repo commit -m "Initial sample Python repository"

ENV PYTHONUNBUFFERED=1 \
    REPO_ROOT=/app/sample_repo \
    AGENT_ALLOW_TESTS=true \
    AGENT_READ_ONLY=false

WORKDIR /app
ENTRYPOINT ["python", "-m", "repo_agent"]
CMD ["demo"]

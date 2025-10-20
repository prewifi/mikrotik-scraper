
# ---- BASE ----
FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl openssh-client \
    && rm -rf /var/lib/apt/lists/*

# ---- DEPENDENCIES ----
COPY requirements-dev.txt .
RUN pip install --upgrade pip && pip install -r requirements-dev.txt

# ---- COPY CODE ----
COPY . .

# # ---- PRE-COMMIT INSTALL ----
# RUN pip install pre-commit commitizen && pre-commit install-hooks

# ---- DEFAULT COMMAND ----
# CMD ["python", "src/main.py"]

CMD ["bash"]
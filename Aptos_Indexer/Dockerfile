# Stage 1: Prepare TypeScript Environment
FROM node:16 AS ts-builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Install ts-node
RUN npm install -g ts-node

# Ensure the compiled scripts are executable (conditionally)
RUN if [ -d "./ts-scripts/dist" ]; then chmod +x ./ts-scripts/dist/*.js; fi

# Stage 2: Build Python Environment
FROM python:3.11
# System deps
RUN pip install "poetry==1.4.2"

# Install Node.js and npm in Python stage
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && npm install -g ts-node \
    && npm install -g npx

ENV HOST 0.0.0.0

WORKDIR /app
COPY poetry.lock pyproject.toml /app/

# Project initialization
RUN poetry config virtualenvs.create false \
    && poetry install --only main

# Copy files and folders
COPY /utils/ /app/utils
COPY /processors/ /app/processors
COPY /scripts/ /app/scripts
COPY constants.py /app/constants.py
COPY config.yaml /app/config.yaml
# Copy everything from the ts-builder stage
COPY --from=ts-builder /app /app


EXPOSE 1000
ENV PORT=1000

# Modify the CMD to execute TypeScript scripts using npx ts-node
CMD ["poetry", "run", "python", "-m", "processors.main", "--config", "/app/config.yaml"]
FROM python:3.12-bullseye

WORKDIR /app

# Upgrade pip first
RUN pip install --upgrade pip

# Copy in your requirements
COPY requirements.txt requirements.txt

# Install pinned versions
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Use FastAPI CLI as entrypoint
ENTRYPOINT [ "fastapi", "run", "main.py" ]


# FROM python:3.12-bullseye

# WORKDIR /app

# COPY requirements.txt requirements.txt

# RUN pip install -r requirements.txt

# COPY . .

# EXPOSE 8000

# ENTRYPOINT [ "fastapi", "run", "main.py" ]

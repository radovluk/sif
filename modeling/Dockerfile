FROM python:3.12-bullseye

# Set a working directory
WORKDIR /app

# Upgrade pip and typing_extensions first
RUN pip install --upgrade pip \
 && pip install --upgrade typing_extensions

# Copy in requirements
COPY requirements.txt requirements.txt

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the rest of the project
COPY . .

# Expose the FastAPI default port
EXPOSE 8000

# Use fastapi CLI as the entrypoint
ENTRYPOINT ["fastapi", "run", "main.py"]


# FROM python:3.12-bullseye

# WORKDIR /app

# COPY requirements.txt requirements.txt

# RUN pip install -r requirements.txt

# COPY . .

# EXPOSE 8000

# ENTRYPOINT [ "fastapi", "run", "main.py" ]

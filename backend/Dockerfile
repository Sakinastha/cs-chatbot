FROM python:3.11-slim

# system deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libffi-dev build-essential default-mysql-client \
 && rm -rf /var/lib/apt/lists/*

# Put the project under /app/backend so imports like "from backend.db" work
WORKDIR /app

# requirements.txt must be in backend/
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# copy backend source into /app/backend (keep your package name)
COPY . /app/backend

# make sure Python can import the /app package root
ENV PYTHONPATH=/app

EXPOSE 5000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "5000"]

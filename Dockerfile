FROM python:3.10-slim

# Enforce clean terminal environment operations parameters
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install explicit OS engine runtime requirements for lightweight processing modules
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy python structural matrices and trigger isolated layer install caching rules
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Export the application logic loop layer into the file stack
COPY main.py .

# Expose default communication port mapped inside stateless Cloud Run switches
EXPOSE 8080

# Spin up web worker configurations optimized for serverless multi-core processors
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
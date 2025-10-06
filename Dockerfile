FROM python:3.11-slim

# Install MySQL client tools
RUN apt-get update && \
    apt-get install -y default-mysql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create virtual environment
RUN python -m venv /app/venv

# Copy requirements and install Python dependencies in venv
COPY requirements.txt .
RUN /app/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy the backup script
COPY mysql_telegram_backup.py .

# Create a directory for temporary files
RUN mkdir -p /tmp/backup

# Set environment variable for temporary directory
ENV TMP_DIR=/tmp/backup

# Add venv to PATH so python commands use the venv
ENV PATH="/app/venv/bin:$PATH"

# Run the backup script using venv python
CMD ["python", "-u", "mysql_telegram_backup.py"]

FROM python:3.11-slim

# Install MySQL client tools
RUN apt-get update && \
    apt-get install -y default-mysql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backup script
COPY mysql_telegram_backup.py .

# Create a directory for temporary files
RUN mkdir -p /tmp/backup

# Set environment variable for temporary directory
ENV TMP_DIR=/tmp/backup

# Run the backup script
CMD ["python", "-u", "mysql_telegram_backup.py"]

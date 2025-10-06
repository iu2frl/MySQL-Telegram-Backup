# MySQL Telegram Backup

A Python script that performs automated MySQL database backups and sends them to a Telegram chat.

## Features

- ✅ Full MySQL database backup using `mysqldump`
- ✅ Support for single database or all databases backup
- ✅ Maximum compression using LZMA/XZ algorithm (preset 9)
- ✅ Automatic file upload to Telegram
- ✅ Retry logic for network failures
- ✅ Comprehensive logging
- ✅ Environment variable configuration
- ✅ Automatic cleanup of temporary files

## Prerequisites

- Python 3.7 or higher
- MySQL client tools (`mysqldump` command)
- A Telegram Bot Token
- Your Telegram Chat ID

### Installing MySQL Client Tools

**Linux (Debian/Ubuntu):**

```bash
sudo apt-get update
sudo apt-get install mysql-client
```

**Linux (Red Hat/CentOS):**

```bash
sudo yum install mysql
```

**Windows:**
Download and install MySQL from [MySQL Downloads](https://dev.mysql.com/downloads/mysql/)

**macOS:**

```bash
brew install mysql-client
```

## Installation

1. Clone this repository:

```bash
git clone <repository-url>
cd MySQL-Telegram-Backup
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

4. Edit `.env` with your actual credentials

## Configuration

Edit the `.env` file with your settings:

```env
# Telegram Bot Configuration
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz  # Get from @BotFather
BOT_DEST=123456789                                # Your chat ID (get from @userinfobot)

# Custom message (optional)
CUST_MSG=Production Database Backup

# MySQL Configuration
MYSQL_HOST=localhost                              # MySQL server host
MYSQL_PORT=3306                                   # MySQL server port
MYSQL_USER=root                                   # MySQL username
MYSQL_PASSWORD=your_secure_password               # MySQL password
MYSQL_DATABASE=                                   # Leave empty for all databases, or specify one

# Temporary Directory (optional)
TMP_DIR=/tmp                                      # Temporary storage location
```

### Getting Your Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the API token provided

### Getting Your Chat ID

1. Search for `@userinfobot` in Telegram
2. Start a conversation with it
3. It will send you your chat ID
4. Alternatively, send a message to your bot and check:

```txt
https://api.telegram.org/bot<YourBOTToken>/getUpdates
```

## Usage

### Option 1: Direct Python Execution

Run the script manually:

```bash
python mysql_telegram_backup.py
```

### Option 2: Docker (Recommended)

The easiest way to run this backup is using Docker. Pre-built images are available on GitHub Container Registry.

#### Pull the Docker image

```bash
docker pull ghcr.io/YOUR_USERNAME/mysql-telegram-backup:latest
```

#### Run with Docker

```bash
docker run --rm \
  -e BOT_TOKEN="your_bot_token" \
  -e BOT_DEST="your_chat_id" \
  -e MYSQL_HOST="your_mysql_host" \
  -e MYSQL_USER="your_mysql_user" \
  -e MYSQL_PASSWORD="your_mysql_password" \
  -e MYSQL_DATABASE="" \
  ghcr.io/YOUR_USERNAME/mysql-telegram-backup:latest
```

#### Run with Docker Compose

1. Create a `.env` file with your configuration
2. Update `docker-compose.yml` with your GitHub username
3. Run:

```bash
docker-compose up
```

#### Scheduled Backups with Docker

Use a cron job to run the Docker container:

```bash
# Add to crontab (crontab -e)
0 2 * * * docker run --rm --env-file /path/to/.env ghcr.io/YOUR_USERNAME/mysql-telegram-backup:latest
```

Or use a container orchestrator like Kubernetes with CronJob.

### Option 3: Automated Backups with Cron (Python)

Add to your crontab for automated daily backups at 2 AM:

```bash
crontab -e
```

Add this line:

```txt
0 2 * * * cd /path/to/MySQL-Telegram-Backup && /usr/bin/python3 mysql_telegram_backup.py
```

### Building Docker Image Locally

If you want to build the image yourself:

```bash
docker build -t mysql-telegram-backup .
docker run --rm --env-file .env mysql-telegram-backup
```

## Compression Details

The script uses LZMA compression with the maximum preset (9) which provides:

- Best compression ratio (typically 70-90% reduction)
- `.xz` file extension
- Slower compression but excellent space savings
- Ideal for database backups sent over networks

## Logging

Logs are created in the temporary directory (default: `/tmp`) with the format:

```txt
YYYYMMDD_HHMMSS_mysql_backup.txt
```

The log file is also sent to Telegram after the backup completes.

## Troubleshooting

### "mysqldump command not found"

Install MySQL client tools (see Prerequisites section)

### "File too large for Telegram"

Telegram has a 2GB file size limit. For larger databases, consider:

- Backing up individual databases separately
- Using a different file transfer method
- Splitting the backup into smaller parts

### "Access denied for user"

Check your MySQL credentials in the `.env` file

### Connection timeout

Increase the timeout value in the script or check your MySQL server accessibility

## Security Notes

- ⚠️ Never commit your `.env` file to version control
- ⚠️ Keep your Telegram bot token secure
- ⚠️ Use strong MySQL passwords
- ⚠️ Consider encrypting backups with a password for sensitive data
- ⚠️ Restrict MySQL user permissions to only what's needed for backups

## License

MIT License - feel free to modify and use as needed.

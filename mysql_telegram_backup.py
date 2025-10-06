import os
import logging
from datetime import datetime
import time
import subprocess
import telebot
from dotenv import load_dotenv
import lzma
import shutil

# Load environment variables from .env file if it exists
load_dotenv()

try:
    LOG_FILE_NAME = datetime.now().strftime("%Y%m%d_%H%M%S") + "_mysql_backup.txt"
    logging.basicConfig(filename=f"/tmp/{LOG_FILE_NAME}", level=logging.DEBUG)
    LOG_FILE_NAME = f"/tmp/{LOG_FILE_NAME}"
except Exception as retEx:
    logging.error("Cannot create log file: [%s]. Defaulting to current folder", str(retEx))
    logging.basicConfig(filename=LOG_FILE_NAME, level=logging.DEBUG)

# Telegram Configuration
TELEGRAM_API_TOKEN: str = os.environ.get('BOT_TOKEN')
if not TELEGRAM_API_TOKEN:
    logging.critical("Input token is empty!")
    raise ValueError("Invalid BOT_TOKEN")
else:
    logging.debug("BOT_TOKEN length: [%s]", len(TELEGRAM_API_TOKEN))

# Get destination chat
TELEGRAM_DEST_CHAT: str = os.environ.get('BOT_DEST')
if not TELEGRAM_DEST_CHAT:
    logging.critical("Destination chat is empty!")
    raise ValueError("Invalid BOT_DEST")
else:
    TELEGRAM_DEST_CHAT: int = int(TELEGRAM_DEST_CHAT)
    logging.debug("BOT_DEST: [%s]", TELEGRAM_DEST_CHAT)

bot = telebot.TeleBot(TELEGRAM_API_TOKEN)

# Custom message to send before backup
TELEGRAM_BACKUP_MESSAGE: str = os.environ.get('CUST_MSG')
if not TELEGRAM_BACKUP_MESSAGE:
    TELEGRAM_BACKUP_MESSAGE = "MySQL Backup at " + datetime.now().strftime("%Y%m%d_%H%M%S")
else:
    TELEGRAM_BACKUP_MESSAGE += "\n\nMySQL Backup at " + datetime.now().strftime("%Y%m%d_%H%M%S")

# MySQL Configuration
MYSQL_HOST: str = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_PORT: str = os.environ.get('MYSQL_PORT', '3306')
MYSQL_USER: str = os.environ.get('MYSQL_USER')
MYSQL_PASSWORD: str = os.environ.get('MYSQL_PASSWORD')
MYSQL_DATABASE: str = os.environ.get('MYSQL_DATABASE')

if not MYSQL_USER:
    logging.critical("MYSQL_USER is empty!")
    raise ValueError("Invalid MYSQL_USER")

if not MYSQL_PASSWORD:
    logging.critical("MYSQL_PASSWORD is empty!")
    raise ValueError("Invalid MYSQL_PASSWORD")

logging.debug("MySQL Configuration - Host: [%s], Port: [%s], User: [%s], Database: [%s]", 
              MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_DATABASE if MYSQL_DATABASE else "ALL")

# Get temporary path
TMP_DIR: str = os.environ.get('TMP_DIR')
if not TMP_DIR:
    TMP_DIR = "/tmp"
    logging.warning("TMP_DIR is empty, falling back to default path: [%s]", TMP_DIR)

TMP_DIR = os.path.join(TMP_DIR, "mysql_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
if not os.path.exists(TMP_DIR):
    try:
        os.makedirs(TMP_DIR, exist_ok=True)
    except Exception as retEx:
        logging.error("Cannot create temporary folder: [%s]. Defaulting to current folder", str(retEx))
        TMP_DIR = os.getcwd()
logging.debug("TMP_DIR: [%s]", TMP_DIR)


def test_mysql_connection():
    """Test MySQL connection and privileges"""
    logging.info("Testing MySQL connection...")
    
    try:
        cmd = [
            "mysql",
            f"--host={MYSQL_HOST}",
            f"--port={MYSQL_PORT}",
            f"--user={MYSQL_USER}",
            f"--password={MYSQL_PASSWORD}",
            "-e", "SELECT 1;"
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logging.info("MySQL connection successful")
            
            # Check privileges
            priv_cmd = [
                "mysql",
                f"--host={MYSQL_HOST}",
                f"--port={MYSQL_PORT}",
                f"--user={MYSQL_USER}",
                f"--password={MYSQL_PASSWORD}",
                "-e", "SHOW GRANTS FOR CURRENT_USER();"
            ]
            
            priv_result = subprocess.run(
                priv_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            if priv_result.returncode == 0:
                logging.info("User privileges: %s", priv_result.stdout)
            
            return True
        else:
            logging.error("MySQL connection failed: [%s]", result.stderr)
            return False
            
    except Exception as e:
        logging.error("Failed to test MySQL connection: [%s]", str(e))
        return False


def perform_mysql_backup(output_file):
    """Perform MySQL backup using mysqldump"""
    logging.info("Starting MySQL backup to: [%s]", output_file)
    
    try:
        # Build mysqldump command
        cmd = [
            "mysqldump",
            f"--host={MYSQL_HOST}",
            f"--port={MYSQL_PORT}",
            f"--user={MYSQL_USER}",
            f"--password={MYSQL_PASSWORD}",
            "--single-transaction",
            "--routines",
            "--triggers",
            "--events",
            "--quick",
            "--lock-tables=false",
            "--no-tablespaces",  # Avoid tablespace errors
            "--skip-add-locks",  # Faster for InnoDB
            "--complete-insert",  # More portable INSERT statements
            "--hex-blob"  # Better binary data handling
        ]
        
        # Add database name if specified, otherwise backup all databases
        if MYSQL_DATABASE:
            cmd.append(MYSQL_DATABASE)
        else:
            cmd.append("--all-databases")
        
        logging.debug("Executing command: %s", ' '.join([c if not c.startswith('--password') else '--password=***' for c in cmd]))
        
        # Execute mysqldump and save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3600  # 1 hour timeout
            )
        
        if result.returncode == 0:
            file_size = os.path.getsize(output_file)
            logging.info("MySQL backup completed successfully. File size: [%d] bytes", file_size)
            
            # Log warnings if any (mysqldump might succeed with warnings)
            if result.stderr:
                logging.warning("mysqldump warnings: [%s]", result.stderr)
            
            # Check if file has actual data (not just structure)
            if file_size < 1024:  # Less than 1KB is suspicious
                logging.warning("Backup file is very small (%d bytes). This might indicate an empty backup.", file_size)
                with open(output_file, 'r', encoding='utf-8') as f:
                    content_preview = f.read(500)
                    logging.debug("File preview: %s", content_preview)
            
            return True
        else:
            logging.error("MySQL backup failed with return code [%d]: [%s]", 
                         result.returncode, result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("MySQL backup timed out after 1 hour")
        return False
    except FileNotFoundError:
        logging.error("mysqldump command not found. Please ensure MySQL client is installed.")
        return False
    except Exception as e:
        logging.error("Failed to perform MySQL backup: [%s]", str(e))
        return False


def compress_file_xz(input_file, output_file):
    """Compress a file using LZMA (xz) with maximum compression"""
    logging.info("Compressing [%s] to [%s] with maximum compression", input_file, output_file)
    
    try:
        with open(input_file, 'rb') as f_in:
            with lzma.open(output_file, 'wb', preset=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        original_size = os.path.getsize(input_file)
        compressed_size = os.path.getsize(output_file)
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        logging.info("Compression completed. Original: [%d] bytes, Compressed: [%d] bytes, Ratio: [%.2f%%]",
                    original_size, compressed_size, compression_ratio)
        return True
        
    except Exception as e:
        logging.error("Failed to compress file: [%s]", str(e))
        return False


def send_file_to_telegram(file_path, max_retries=3):
    """Send a file to Telegram with retry logic"""
    sent = False
    
    for attempt in range(max_retries):
        try:
            with open(file_path, 'rb') as f:
                bot.send_document(TELEGRAM_DEST_CHAT, f)
            logging.info("File [%s] sent successfully to Telegram", file_path)
            sent = True
            break
            
        except Exception as retEx:
            error_str = str(retEx)
            
            if "413" in error_str or "Request Entity Too Large" in error_str:
                logging.error("File too large to send via Telegram: [%s]", retEx)
                try:
                    bot.send_message(TELEGRAM_DEST_CHAT, 
                                   f"Cannot send file `{os.path.basename(file_path)}`: File too large for Telegram")
                except Exception as sendEx:
                    logging.error("Failed to send error message: [%s]", sendEx)
                break
                
            if attempt < max_retries - 1:
                logging.warning("Failed to send file, retrying in 5 seconds... (%d/%d)", 
                              attempt + 1, max_retries)
                time.sleep(5)
            else:
                logging.error("Cannot send file after %d attempts: [%s]", max_retries, retEx)
                try:
                    bot.send_message(TELEGRAM_DEST_CHAT, 
                                   f"Cannot send file `{os.path.basename(file_path)}`: {str(retEx)}")
                except Exception as sendEx:
                    logging.error("Failed to send error message: [%s]", sendEx)
    
    return sent


def cleanup_file(file_path):
    """Delete a file safely"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.debug("File [%s] deleted successfully", file_path)
    except Exception as retEx:
        logging.error("Error while deleting [%s]: [%s]", file_path, retEx)


if __name__ == '__main__':
    try:
        # Send initial message
        bot.send_message(TELEGRAM_DEST_CHAT, TELEGRAM_BACKUP_MESSAGE)
        logging.info("Starting MySQL backup process")
        
        # Test MySQL connection first
        bot.send_message(TELEGRAM_DEST_CHAT, "🔍 Testing MySQL connection...")
        if not test_mysql_connection():
            error_msg = "❌ Failed to connect to MySQL. Check credentials and connection."
            bot.send_message(TELEGRAM_DEST_CHAT, error_msg)
            logging.error(error_msg)
            raise Exception("MySQL connection test failed")
        
        bot.send_message(TELEGRAM_DEST_CHAT, "✅ MySQL connection successful")
        
        # Create temporary output path
        if not os.path.exists(TMP_DIR):
            logging.info("Creating temporary folder: [%s]", TMP_DIR)
            os.makedirs(TMP_DIR, exist_ok=True)
        else:
            logging.warning("Folder [%s] already exists", TMP_DIR)
        
        # Define file paths
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        database_name = MYSQL_DATABASE if MYSQL_DATABASE else "all_databases"
        sql_file = os.path.join(TMP_DIR, f"mysql_{database_name}_{timestamp}.sql")
        compressed_file = os.path.join(TMP_DIR, f"mysql_{database_name}_{timestamp}.sql.xz")
        
        # Perform MySQL backup
        bot.send_message(TELEGRAM_DEST_CHAT, "💾 Starting database backup...")
        if perform_mysql_backup(sql_file):
            bot.send_message(TELEGRAM_DEST_CHAT, "✅ MySQL backup completed, starting compression...")
            
            # Compress the SQL file
            if compress_file_xz(sql_file, compressed_file):
                bot.send_message(TELEGRAM_DEST_CHAT, "✅ Compression completed, sending file...")
                
                # Send compressed file to Telegram
                if send_file_to_telegram(compressed_file):
                    bot.send_message(TELEGRAM_DEST_CHAT, "✅ Backup file sent successfully!")
                else:
                    bot.send_message(TELEGRAM_DEST_CHAT, "❌ Failed to send backup file")
                
                # Cleanup compressed file
                cleanup_file(compressed_file)
            else:
                bot.send_message(TELEGRAM_DEST_CHAT, "❌ Failed to compress backup file")
            
            # Cleanup SQL file
            cleanup_file(sql_file)
        else:
            bot.send_message(TELEGRAM_DEST_CHAT, "❌ MySQL backup failed")
            logging.error("MySQL backup failed")
        
        # Send log file
        logging.info("Sending log file")
        if send_file_to_telegram(LOG_FILE_NAME):
            logging.info("Log file sent successfully")
        
        # Cleanup temporary directory
        try:
            if os.path.exists(TMP_DIR) and os.path.isdir(TMP_DIR):
                shutil.rmtree(TMP_DIR)
                logging.info("Temporary directory cleaned up")
        except Exception as e:
            logging.error("Failed to cleanup temporary directory: [%s]", str(e))
        
        logging.info("MySQL backup process completed!")
        
    except Exception as e:
        error_msg = f"Fatal error during backup: {str(e)}"
        logging.critical(error_msg)
        try:
            bot.send_message(TELEGRAM_DEST_CHAT, f"❌ {error_msg}")
        except:
            pass

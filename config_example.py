# Configuration for disk_health_monitor.py

# Set to None to use journalctl instead of a log file
LOG_FILE = '/var/log/messages'  # or None

# Email settings
EMAIL_FROM = 'admin@example.com'
EMAIL_TO = 'you@example.com'

# SMTP server settings
SMTP_SERVER = 'smtp.example.com'
SMTP_PORT = 587
SMTP_USER = 'smtp_user'
SMTP_PASS = 'smtp_password'

# Disk Health Monitor

Python script to monitor disk health on Red Hat Linux systems using SMART data and system logs, with email alerting and repair functionality.

## Features

- Checks SMART health status of all disks using `smartctl`
- Parses system logs or journalctl for disk-related errors
- Sends email alerts if any disk issues are detected
- Interactive filesystem repair with automatic unmount before running `fsck`

## Requirements

- Python 3.x
- `smartmontools` installed (`sudo yum install smartmontools`)
- SMTP server credentials for sending email
- Run with root privileges for full access

## Installation

1. Clone this repository or download the files.
2. Copy `config_example.py` to `config.py` and update your configuration.
3. Run the script as root or with sudo:

```bash
sudo python3 disk_health_monitor.py

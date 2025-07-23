#!/usr/bin/env python3
import subprocess
import re
import smtplib
from email.message import EmailMessage

# === Configuration ===
try:
    import config
except ImportError:
    print("Please create a config.py file based on config_example.py")
    exit(1)

def get_disks():
    try:
        result = subprocess.run(['lsblk', '-dn', '-o', 'NAME,TYPE'], capture_output=True, text=True)
        disks = []
        for line in result.stdout.strip().split('\n'):
            name, typ = line.split()
            if typ == 'disk':
                disks.append(f"/dev/{name}")
        return disks
    except Exception as e:
        print(f"Error getting disks: {e}")
        return []

def get_partitions(disk):
    """Return list of partitions for a given disk, e.g. ['/dev/sda1', '/dev/sda2']"""
    try:
        result = subprocess.run(['lsblk', '-ln', '-o', 'NAME,TYPE', disk], capture_output=True, text=True)
        partitions = []
        for line in result.stdout.strip().split('\n'):
            name, typ = line.split()
            if typ == 'part':
                partitions.append(f"/dev/{name}")
        return partitions
    except Exception as e:
        print(f"Error getting partitions for {disk}: {e}")
        return []

def check_smart_status(disk):
    try:
        result = subprocess.run(['smartctl', '-H', disk], capture_output=True, text=True)
        output = result.stdout
        match = re.search(r'SMART overall-health self-assessment test result: (\w+)', output)
        if match:
            return match.group(1)
        else:
            return "UNKNOWN"
    except Exception as e:
        print(f"Error checking SMART status for {disk}: {e}")
        return "ERROR"

def parse_log_for_errors():
    errors = []
    try:
        if config.LOG_FILE:
            with open(config.LOG_FILE, 'r') as f:
                logs = f.readlines()
        else:
            result = subprocess.run(['journalctl', '-k', '--since', '1 hour ago'], capture_output=True, text=True)
            logs = result.stdout.splitlines()
        
        error_keywords = ['I/O error', 'ata_error', 'fail', 'error', 'unresponsive', 'offline', 'faulty']
        for line in logs:
            if any(keyword.lower() in line.lower() for keyword in error_keywords):
                errors.append(line.strip())
    except Exception as e:
        print(f"Error parsing logs: {e}")
    return errors

def send_email(subject, body):
    try:
        msg = EmailMessage()
        msg['From'] = config.EMAIL_FROM
        msg['To'] = config.EMAIL_TO
        msg['Subject'] = subject
        msg.set_content(body)

        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.send_message(msg)
        print("Alert email sent.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def is_mounted(device):
    """Check if a device (partition) is mounted"""
    try:
        result = subprocess.run(['mountpoint', '-q', device])
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking mountpoint for {device}: {e}")
        return False

def repair_filesystem(device):
    """
    Attempt to repair filesystem on device using fsck.
    If the device is mounted, try to unmount it first.
    """
    try:
        if is_mounted(device):
            print(f"{device} is currently mounted. Attempting to unmount...")
            umount_result = subprocess.run(['umount', device], capture_output=True, text=True)
            if umount_result.returncode != 0:
                print(f"Failed to unmount {device}: {umount_result.stderr.strip()}")
                print("Skipping repair for this partition.")
                return False
            else:
                print(f"Successfully unmounted {device}.")
        else:
            print(f"{device} is not mounted. Proceeding with repair.")

        print(f"Running fsck on {device}...")
        result = subprocess.run(['fsck', '-y', device], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode == 0:
            print(f"Filesystem on {device} repaired successfully or no issues found.")
            return True
        else:
            print(f"fsck returned exit code {result.returncode}. Please review output.")
            return False
    except Exception as e:
        print(f"Error running fsck on {device}: {e}")
        return False

def prompt_repair(disks):
    """Prompt user to repair partitions of disks with issues"""
    for disk in disks:
        print(f"\nDisk {disk} has issues. Checking partitions for repair...")
        partitions = get_partitions(disk)
        if not partitions:
            print(f"No partitions found on {disk}.")
            continue

        for part in partitions:
            mounted = is_mounted(part)
            status = "mounted" if mounted else "unmounted"
            print(f"Partition {part} is {status}.")

            while True:
                ans = input(f"Do you want to run fsck repair on {part}? (yes/no): ").strip().lower()
                if ans in ('yes', 'y'):
                    repair_filesystem(part)
                    break
                elif ans in ('no', 'n'):
                    print(f"Skipping repair on {part}.")
                    break
                else:
                    print("Please answer 'yes' or 'no'.")

def main():
    disks = get_disks()
    if not disks:
        print("No disks found.")
        return

    failed_disks = []
    for disk in disks:
        status = check_smart_status(disk)
        print(f"{disk}: SMART status = {status}")
        if status.lower() != 'passed':
            failed_disks.append(disk)

    log_errors = parse_log_for_errors()
    if log_errors:
        print("\nDisk-related errors found in system logs:")
        for err in log_errors:
            print(err)

    if failed_disks or log_errors:
        subject = "Disk Health Alert on Red Hat System"
        body = "The following disk issues were detected:\n\n"
        if failed_disks:
            body += "Failed or failing disks (SMART):\n"
            for fdisk in failed_disks:
                body += f" - {fdisk}\n"
            body += "\n"
        if log_errors:
            body += "Disk-related errors from system logs:\n"
            for err in log_errors:
                body += f" - {err}\n"
        send_email(subject, body)

        # Prompt for repair on failed disks
        prompt_repair(failed_disks)
    else:
        print("\nAll disks passed SMART checks and no disk errors found in logs.")

if __name__ == "__main__":
    main()

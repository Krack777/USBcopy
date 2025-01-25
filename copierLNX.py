import os
import shutil
import time
from datetime import datetime
import pyudev

BACKUP_FOLDER_TEMP = "/tmp/usb_temp_backup"

def is_usb_drive(device):
    try:
        if device.get('ID_BUS') == 'usb' and device.get('DEVTYPE') == 'partition':
            return True
        return False
    except Exception:
        return False

def list_available_drives():
    drives = {}
    context = pyudev.Context()

    for idx, device in enumerate(context.list_devices(subsystem='block', DEVTYPE='partition'), start=1):
        if is_usb_drive(device):
            mount_point = device.attributes.asstring('mountpoint') if 'mountpoint' in device.attributes else None
            size = device.attributes.asstring('size') if 'size' in device.attributes else "Unknown"
            if mount_point:
                drives[idx] = {
                    "device": device.device_node,
                    "size": f"{int(size) // (1024 * 1024 * 1024)} GB",
                    "mount_point": mount_point,
                }
    return drives

def choose_backup_drive():
    drives = list_available_drives()
    if not drives:
        print("NO AVAILABLE DRIVES FOUND!")
        exit(1)

    print("AVAILABLE DRIVES:")
    for idx, info in drives.items():
        print(f"{idx}: {info['mount_point']} (Device: {info['device']}, Size: {info['size']})")

    while True:
        try:
            choice = int(input("CHOOSE DRIVE TO SAVE BACKUP (NUMBER): "))
            if choice in drives:
                return drives[choice]['mount_point']
        except ValueError:
            pass
        print("INVALID CHOICE. PLEASE TRY AGAIN.")

def backup_usb_to_temp(mount_point):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = os.path.join(BACKUP_FOLDER_TEMP, f"USB_Backup_{timestamp}")
    os.makedirs(backup_path, exist_ok=True)

    print(f"STARTING TEMP BACKUP FROM {mount_point} TO {backup_path}...")

    try:
        for root, dirs, files in os.walk(mount_point):
            relative_path = os.path.relpath(root, mount_point)
            target_root = os.path.join(backup_path, relative_path)

            os.makedirs(target_root, exist_ok=True)

            for file in files:
                source_file = os.path.join(root, file)
                target_file = os.path.join(target_root, file)
                shutil.copy2(source_file, target_file)

        print(f"TEMP BACKUP SUCCESS: {backup_path}")
    except Exception as e:
        print(f"ERROR DURING TEMP BACKUP: {e}")
    return backup_path

def copy_temp_to_final(temp_path, final_drive):
    final_path = os.path.join(final_drive, os.path.basename(temp_path))
    print(f"COPYING BACKUP FROM {temp_path} TO {final_path}...")

    try:
        shutil.copytree(temp_path, final_path)
        print(f"FINAL BACKUP SUCCESS: {final_path}")
    except Exception as e:
        print(f"ERROR DURING FINAL BACKUP: {e}")

def monitor_usb(final_backup_drive):
    print("WAITING FOR USB...")
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='block', device_type='partition')

    for device in iter(monitor.poll, None):
        if device.action == 'add' and is_usb_drive(device):
            mount_point = device.get('ID_FS_MOUNTPOINT')
            if mount_point:
                print(f"USB FOUND: {mount_point}")
                temp_backup_path = backup_usb_to_temp(mount_point)
                copy_temp_to_final(temp_backup_path, final_backup_drive)

if __name__ == "__main__":
    os.makedirs(BACKUP_FOLDER_TEMP, exist_ok=True)
    final_backup_drive = choose_backup_drive()
    monitor_usb(final_backup_drive)

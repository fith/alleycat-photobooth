#!/bin/bash
#
# USB RAID 1 Mirror Setup Script
# ------------------------------
# This script sets up a RAID 1 mirror using two USB flash drives on a Raspberry Pi
# The RAID array is mounted at /mnt/usbdata and configured for automounting
#

# Exit on error
set -e

# Function to print colored output
print_message() {
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
    
    case $1 in
        "info")
            echo -e "${GREEN}[INFO]${NC} $2"
            ;;
        "error")
            echo -e "${RED}[ERROR]${NC} $2"
            ;;
        "warning")
            echo -e "${YELLOW}[WARNING]${NC} $2"
            ;;
        *)
            echo "$2"
            ;;
    esac
}

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_message "error" "This script must be run as root. Try 'sudo $0'"
    exit 1
fi

# Install required packages
print_message "info" "Installing required packages..."
apt-get update
apt-get install -y mdadm

# Identify USB drives
print_message "info" "Listing available drives..."
lsblk
echo ""

# Prompt for drive selection
read -p "Enter the first USB drive (e.g., sda): " DRIVE1
read -p "Enter the second USB drive (e.g., sdb): " DRIVE2

DRIVE1="/dev/${DRIVE1}"
DRIVE2="/dev/${DRIVE2}"

# Verify drives exist
if [ ! -b "${DRIVE1}" ] || [ ! -b "${DRIVE2}" ]; then
    print_message "error" "One or both of the selected drives do not exist."
    exit 1
fi

# Check drives are not the same
if [ "${DRIVE1}" = "${DRIVE2}" ]; then
    print_message "error" "You must select two different drives."
    exit 1
fi

# Confirm selection
print_message "warning" "This will ERASE ALL DATA on ${DRIVE1} and ${DRIVE2}!"
read -p "Are you sure you want to continue? (y/n): " CONFIRM
if [ "${CONFIRM}" != "y" ]; then
    print_message "info" "Operation canceled."
    exit 0
fi

# Create partitions on both drives
print_message "info" "Creating partitions on both drives..."

# Create partition on first drive
echo -e "o\nn\np\n1\n\n\nw" | fdisk ${DRIVE1}

# Create partition on second drive
echo -e "o\nn\np\n1\n\n\nw" | fdisk ${DRIVE2}

# Reload partition table
partprobe ${DRIVE1}
partprobe ${DRIVE2}

# Ensure we use the first partition
DRIVE1P="${DRIVE1}1"
DRIVE2P="${DRIVE2}1"

# Wait for partitions to be available
sleep 2

# Create the RAID 1 array
print_message "info" "Creating RAID 1 array..."
mdadm --create --verbose /dev/md0 --level=1 --raid-devices=2 ${DRIVE1P} ${DRIVE2P}

# Wait for array to initialize
print_message "info" "Waiting for array to initialize..."
sleep 5

# Format the RAID array as vfat
print_message "info" "Formatting RAID array as vfat..."
mkfs.vfat /dev/md0

# Create mount point
print_message "info" "Creating mount point..."
mkdir -p /mnt/usbdata

# Mount the RAID array
print_message "info" "Mounting RAID array..."
mount -t vfat -o rw,uid=1000,gid=1000,umask=0022 /dev/md0 /mnt/usbdata

# Save RAID configuration
print_message "info" "Saving RAID configuration..."
mdadm --detail --scan >> /etc/mdadm/mdadm.conf
update-initramfs -u

# Configure automounting
print_message "info" "Configuring automounting..."
echo "/dev/md0 /mnt/usbdata vfat defaults,uid=1000,gid=1000,umask=0022,auto,nofail 0 0" >> /etc/fstab

# Reload systemd to recognize the new fstab entry
print_message "info" "Reloading systemd daemon..."
systemctl daemon-reload

# Test the setup
print_message "info" "Testing RAID setup..."
umount /mnt/usbdata
mount /mnt/usbdata

# Verify the RAID setup
print_message "info" "Verifying RAID configuration..."
# Check RAID status
RAID_STATUS=$(mdadm --detail /dev/md0)
echo "$RAID_STATUS"

# Check if both drives are active in the array
if echo "$RAID_STATUS" | grep -q "${DRIVE1P}" && echo "$RAID_STATUS" | grep -q "${DRIVE2P}"; then
    if echo "$RAID_STATUS" | grep -q "State : clean" || echo "$RAID_STATUS" | grep -q "State : active"; then
        print_message "info" "RAID verification passed: Both drives are active in the array."
    else
        print_message "warning" "RAID array is not in clean state. It may still be syncing."
    fi
else
    print_message "error" "RAID verification failed: Not all drives are active in the array."
fi

# Verify we can write to the array
print_message "info" "Testing write access to RAID array..."
TEST_FILE="/mnt/usbdata/raid_test_file.txt"
echo "This is a test file to verify RAID functionality." > "$TEST_FILE"
if [ -f "$TEST_FILE" ]; then
    print_message "info" "Write test passed: Successfully created test file."
    cat "$TEST_FILE"
    rm "$TEST_FILE"
else
    print_message "error" "Write test failed: Could not create test file."
fi

# Final instructions
print_message "info" "RAID 1 mirror setup complete!"
print_message "info" "Your USB drives are now mirrored and mounted at /mnt/usbdata"
print_message "info" "The array will automatically mount on boot."
print_message "info" ""
print_message "info" "To check RAID status: sudo mdadm --detail /dev/md0"
print_message "info" "If a drive fails, replace it and run: sudo mdadm --manage /dev/md0 --add /dev/sdXY"

exit 0 
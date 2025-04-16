#!/bin/bash
#
# I2C LCD Display Setup Script for Raspberry Pi
# --------------------------------------------
# This script enables I2C on the Raspberry Pi and provides
# information about setting up a 16x2 LCD display
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

# Display setup information
print_message "info" "Setting up I2C for LCD Display on Raspberry Pi"
print_message "info" "This script will enable I2C interface at the system level"
print_message "info" ""
print_message "info" "LCD Wiring Guide:"
print_message "info" "- VCC on LCD → 5V on Raspberry Pi (Pin 2 or 4)"
print_message "info" "- GND on LCD → GND on Raspberry Pi (Pin 6, 9, 14, or 20)"
print_message "info" "- SDA on LCD → GPIO 2 (Pin 3) on Raspberry Pi"
print_message "info" "- SCL on LCD → GPIO 3 (Pin 5) on Raspberry Pi"
echo ""

# Confirm to proceed
read -p "Continue with I2C setup? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    print_message "info" "Setup cancelled."
    exit 0
fi

# Enable I2C interface
print_message "info" "Enabling I2C interface..."
raspi-config nonint do_i2c 0
if [ $? -eq 0 ]; then
    print_message "info" "I2C interface enabled successfully"
else
    print_message "error" "Failed to enable I2C interface"
    exit 1
fi

# Install required system packages
print_message "info" "Installing required system packages..."
apt-get update
apt-get install -y i2c-tools

# Detect I2C devices
print_message "info" "Detecting I2C devices..."
print_message "info" "Your LCD should appear at address 0x27 or 0x3F when connected properly"
i2cdetect -y 1
echo ""

# Information about using I2C in Docker
print_message "info" ""
print_message "info" "============ LCD Display Integration ============"
print_message "info" ""
print_message "info" "To use the I2C LCD display in Docker containers:"
print_message "info" ""
print_message "info" "1. Add this volume to your container in docker-compose.yml:"
print_message "info" "   - /dev/i2c-1:/dev/i2c-1"
print_message "info" ""
print_message "info" "2. Common I2C addresses for these displays:"
print_message "info" "   - 0x27 (most common)"
print_message "info" "   - 0x3F (alternative address)"
print_message "info" ""
print_message "info" "3. Verify I2C connection:"
print_message "info" "   - Run 'i2cdetect -y 1' to see connected devices"
print_message "info" ""
print_message "info" "4. Hardware verification:"
print_message "info" "   - The display should have a blue backlight when powered"
print_message "info" "   - Check connections if not lit"
print_message "info" "   - Use a multimeter to verify 5V power at the display"
print_message "info" ""
print_message "info" "I2C setup complete! The system is now ready for I2C devices."

exit 0 
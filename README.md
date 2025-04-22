# Alleycat Photobooth

A Raspberry Pi-based photobooth system with RFID card reading and video recording capabilities.

## Hardware Connections

### GPIO Pin Assignments (BCM mode)
Physical pin numbers in parentheses for reference

#### RFID Reader (MFRC522)
- RST: GPIO 22 (Pin 15)
- SPI Interface (default pins):
  - MOSI: GPIO 10 (Pin 19)
  - MISO: GPIO 9 (Pin 21)
  - SCLK: GPIO 11 (Pin 23)
  - CE0: GPIO 8 (Pin 24)
- IRQ: GPIO 18 (Pin 12)

#### LCD Display (PCF8574 I2C Backpack)
- I2C Interface (default pins):
  - SDA: GPIO 2 (Pin 3)
  - SCL: GPIO 3 (Pin 5)
- I2C Address: 0x27

#### Button and LEDs
- Button Input: BCM 16 (Physical pin 36)
- Button LED: BCM 20 (Physical pin 38)
- Green LED: BCM 21 (Physical pin 40)
- Yellow LED: BCM 23 (Physical pin 16)
- Red LED: BCM 15 (Physical pin 10)
- Blue LED: BCM 24 (Physical pin 18)

### Other Hardware
- Webcam: USB device (mounted at /dev/video0)
- USB Storage: Mounted at /mnt/usbdata

## Software Requirements
- Python 3.12
- Flask 3.0.2
- RPi.GPIO 0.7.1
- mfrc522 0.0.7
- ffmpeg-python 0.2.0
- python-dotenv 0.19.0
- pysmb 1.2.9.1
- spidev 3.6
- smbus2 0.4.1
- RPLCD 1.4.0

## Setup Instructions
1. Connect hardware according to pin assignments above
2. Mount USB storage at /mnt/usbdata
3. Build and run Docker container:
   ```bash
   docker compose up --build
   ```

## Notes
- The system uses hardware-accelerated video encoding via /dev/dri
- GPIO pins are configured in BCM mode
- All data is stored on the USB drive at /mnt/usbdata 
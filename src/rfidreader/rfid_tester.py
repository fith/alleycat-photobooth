import RPi.GPIO as GPIO
import spidev
import time

# Constants for SPI
SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED = 1000000  # 1MHz

# Initialize SPI
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_DEVICE)
spi.max_speed_hz = SPI_SPEED

def read_rfid():
    try:
        # Send a read command (this will vary based on your specific RFID reader)
        # This is a basic example - you'll need to adjust based on your reader's protocol
        response = spi.xfer2([0x01, 0x00, 0x00, 0x00])
        print(f"SPI Response: {response}")
        return response
    except Exception as e:
        print(f"Error reading RFID: {e}")
        return None

def main():
    print("Starting RFID Reader Test...")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            data = read_rfid()
            if data:
                print(f"Received data: {data}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        spi.close()
        GPIO.cleanup()

if __name__ == "__main__":
    main()

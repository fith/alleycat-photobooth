#!/usr/bin/env python3
"""
RFID reader script for the Raspberry Pi.
Reads RFID tags using the MFRC522 module and returns the UID.

Usage:
    python rfid.py scan [timeout]
"""

import sys
import time
import RPi.GPIO as GPIO
from mfrc522 import MFRC522

# Import from our custom logger module
from .logger import log, DEBUG

# Define GPIO pins for MFRC522 connection
RST_PIN = 22    # GPIO 22 (Pin 15)

def init_rfid():
    """Initialize the RFID reader"""
    try:
        # Set GPIO mode
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Explicitly configure RST pin with pull-up
        GPIO.setup(RST_PIN, GPIO.OUT, initial=GPIO.HIGH)
        
        # Initialize the MFRC522
        reader = MFRC522(pin_rst=RST_PIN)
        
        # Try to read the version register to check if it's working
        version = reader.Read_MFRC522(reader.VersionReg)
        if version == 0xFF:
            log(f"Failed to read version register (got 0xFF)")
            return None
            
        if version != 0x92 and version != 0x91:
            log(f"Unexpected RC522 version: 0x{version:02x}")
            
        log(f"RC522 Version: 0x{version:02x}")
        
        # Configure antenna gain for optimal reading
        reader.AntennaOn()
        
        return reader
    
    except Exception as e:
        log(f"Error initializing RFID reader: {e}")
        return None

def scan_rfid(reader, timeout=None):
    """Scan for RFID tags
    
    Args:
        reader: Initialized MFRC522 reader
        timeout: Maximum time to wait for a card in seconds (None = wait forever)
        
    Returns:
        UID string or None if timeout or error
    """
    if reader is None:
        log("RFID reader not initialized")
        return None
    
    start_time = time.time()
    
    try:
        # Keep scanning until timeout
        while timeout is None or (time.time() - start_time) < timeout:
            # Reset the antenna gain for optimal reading distance
            reader.AntennaOn()
            
            # Look for cards
            (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
            
            if status == reader.MI_OK:
                # Get the UID of the card
                (status, uid) = reader.MFRC522_Anticoll()
                
                if status == reader.MI_OK:
                    # Format the UID for display
                    uid_str = '-'.join([f"{x:02x}" for x in uid])
                    log(f"Card detected! Type: {TagType}")
                    log(f"Card UID: {uid_str}")
                    
                    # Select the card
                    reader.MFRC522_SelectTag(uid)
                    
                    # Halt the card to release it
                    reader.MFRC522_StopCrypto1()
                    
                    return uid_str
            
            # Short delay between scans
            time.sleep(0.1)
        
        # If we get here, we timed out
        log("Timeout: No card detected")
        return None
        
    except Exception as e:
        log(f"Error scanning for RFID: {e}")
        return None

        # Clean up is done by the caller

def cleanup():
    """Clean up GPIO pins"""
    GPIO.cleanup()
    log("GPIO cleanup completed")

def main():
    """Main function"""
    command = sys.argv[1].lower() if len(sys.argv) > 1 else "help"
    
    if command == "scan":
        # Get timeout (optional argument)
        timeout = float(sys.argv[2]) if len(sys.argv) > 2 else None
        
        try:
            # Initialize reader
            reader = init_rfid()
            if reader is None:
                log("Failed to initialize RFID reader")
                sys.exit(1)
            
            # Scan for cards
            log("Scanning for RFID tags...")
            if timeout:
                log(f"Timeout set to {timeout} seconds")
                
            uid = scan_rfid(reader, timeout)
            
            if uid:
                log(f"RFID tag detected: {uid}")
                sys.exit(0)
            else:
                log("No RFID tag detected")
                sys.exit(2)  # Exit code 2 for timeout
                
        finally:
            # Always clean up
            cleanup()
    
    else:
        log("Usage:")
        log("  python rfid.py scan [timeout]")
        sys.exit(1)

if __name__ == "__main__":
    # Check if correct number of arguments are provided
    if len(sys.argv) < 2:
        log("Usage:")
        log("  python rfid.py scan [timeout]")
        sys.exit(1)
    
    main() 
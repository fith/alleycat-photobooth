#!/usr/bin/env python3
"""
RFID reader script for the Raspberry Pi.
Reads NeoBand tags using the MFRC522 module and returns structured data.

Usage:
    python rfid.py scan [timeout]
"""

import sys
import time
import RPi.GPIO as GPIO
from mfrc522 import MFRC522
from common.logit import log, DEBUG

# Define GPIO pins for MFRC522 connection
RST_PIN = 22    # GPIO 22 (Pin 15)

# NeoBand configuration
NEOBAND_KEY_A = [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5]  # Key A for reading
AUTH_MODE = 0x60  # Authentication mode

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

def read_block(reader, sector, block):
    """Read a block from the RFID tag"""
    try:
        # Authenticate with Key A
        status = reader.MFRC522_Auth(reader.PICC_AUTHENT1A, block, NEOBAND_KEY_A, reader.uid)
        if status != reader.MI_OK:
            log(f"Authentication failed for sector {sector}, block {block}")
            return None
            
        # Read the block
        status, data = reader.MFRC522_Read(block)
        if status != reader.MI_OK:
            log(f"Failed to read sector {sector}, block {block}")
            return None
            
        return data
        
    except Exception as e:
        log(f"Error reading block: {e}")
        return None

def hex_to_text(hex_data):
    """Convert hex data to text, removing null bytes and trailing garbage"""
    try:
        # Convert hex bytes to string, removing null bytes and trailing garbage
        text = bytes(hex_data).decode('utf-8', errors='ignore').strip('\x00')
        return text
    except Exception as e:
        log(f"Error converting hex to text: {e}")
        return None

def scan_rfid(reader, timeout=None):
    """Scan for RFID tags and read NeoBand data
    
    Args:
        reader: Initialized MFRC522 reader
        timeout: Maximum time to wait for a card in seconds (None = wait forever)
        
    Returns:
        Dictionary with NeoBand data or None if timeout or error
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
                    neo_id = '-'.join([f"{x:02x}" for x in uid])
                    log(f"Card detected! Type: {TagType}")
                    log(f"Card UID: {neo_id}")
                    
                    # Select the card
                    reader.MFRC522_SelectTag(uid)
                    
                    # Read role (Sector 1, Block 0)
                    role_data = read_block(reader, 1, 0)
                    role = hex_to_text(role_data) if role_data else None
                    
                    # Read name (Sector 39, Block 0)
                    name_data = read_block(reader, 39, 0)
                    name = hex_to_text(name_data) if name_data else None
                    
                    # Read allegiance (Sector 39, Block 1)
                    allegiance_data = read_block(reader, 39, 1)
                    allegiance = hex_to_text(allegiance_data) if allegiance_data else None
                    
                    # Determine faction based on sector
                    faction = f"faction{uid[0] % 31 + 1}"  # Simple mapping based on UID
                    
                    # Halt the card to release it
                    reader.MFRC522_StopCrypto1()
                    
                    # Return structured data
                    return {
                        "role": role,
                        "name": name,
                        "allegiance": allegiance,
                        "neoId": neo_id,
                        "faction": faction
                    }
            
            # Short delay between scans
            time.sleep(0.1)
        
        # If we get here, we timed out
        # log("Timeout: No card detected")
        return None
        
    except Exception as e:
        log(f"Error scanning for RFID: {e}")
        return None

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
                
            data = scan_rfid(reader, timeout)
            
            if data:
                log(f"NeoBand data: {data}")
                sys.exit(0)
            else:
                log("No RFID tag detected or error reading data")
                sys.exit(2)  # Exit code 2 for timeout/error
                
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
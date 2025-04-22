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
from logit import log, DEBUG
import csv
from datetime import datetime

# Define GPIO pins for MFRC522 connection
RST_PIN = 22    # GPIO 22 (Pin 15)

# NeoBand configuration
NEOBAND_KEY_A = [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5]  # Key A for reading
AUTH_MODE = 0x60  # Authentication mode

# Global reader instance
_reader = None

def init_rfid():
    """Initialize the RFID reader"""
    global _reader
    try:
        # Set GPIO mode
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Explicitly configure RST pin with pull-up
        GPIO.setup(RST_PIN, GPIO.OUT, initial=GPIO.HIGH)
        
        # Initialize the MFRC522
        _reader = MFRC522(pin_rst=RST_PIN)
        
        # Try to read the version register to check if it's working
        version = _reader.Read_MFRC522(_reader.VersionReg)
        if version == 0xFF:
            log(f"Failed to read version register (got 0xFF)")
            return None
            
        if version != 0x92 and version != 0x91:
            log(f"Unexpected RC522 version: 0x{version:02x}")
            
        log(f"RC522 Version: 0x{version:02x}")
        
        # Configure antenna gain for optimal reading
        _reader.AntennaOn()
        
        return _reader
    
    except Exception as e:
        log(f"Error initializing RFID reader: {e}")
        return None

def read_block(reader, sector, block):
    """Read a block from the RFID tag"""
    try:
        # Read the block - MFRC522_Read takes block number (0-63)
        block_num = sector * 4 + block  # Convert sector/block to absolute block number
        (status, data) = reader.MFRC522_Read(block_num)
        if status == reader.MI_OK:
            return data
        log(f"Error reading block {block_num}: status={status}")
        return None
    except Exception as e:
        log(f"Error reading block: {e}")
        return None

def hex_to_text(hex_data):
    """Convert hex data to text"""
    if not hex_data:
        return None
    try:
        # Convert hex to bytes, then decode
        text = bytes(hex_data).decode('utf-8').strip('\x00')
        return text if text else None
    except Exception as e:
        log(f"Error converting hex to text: {e}")
        return None

def log_rfid_scan(data):
    """Log RFID scan to CSV file"""
    try:
        with open('/data/rfid_log.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                data.get('neoId', ''),
                data.get('name', ''),
                data.get('role', ''),
                data.get('allegiance', ''),
                data.get('faction', '')
            ])
    except Exception as e:
        log(f"Error logging RFID scan: {e}")

def scan_rfid():
    """Scan for RFID tags and read NeoBand data"""
    global _reader
    
    # Initialize reader if not already done
    if _reader is None:
        _reader = init_rfid()
        if _reader is None:
            return None
    
    try:
        # Look for cards
        (status, TagType) = _reader.MFRC522_Request(_reader.PICC_REQIDL)
        
        if status != _reader.MI_OK:
            return None
            
        # Get the UID
        (status, uid) = _reader.MFRC522_Anticoll()
        
        if status != _reader.MI_OK:
            return None
            
        # Format the UID
        neo_id = '-'.join([f"{x:02x}" for x in uid])
        
        # Select the card
        if _reader.MFRC522_SelectTag(uid) != _reader.MI_OK:
            return None
        
        # Read role (Sector 1, Block 0)
        role_data = read_block(_reader, 1, 0)
        role = hex_to_text(role_data) if role_data else 'bounty'
        
        # Read name (Sector 39, Block 0)
        name_data = read_block(_reader, 39, 0)
        name = hex_to_text(name_data) if name_data else 'Unknown'
        
        # Read allegiance (Sector 39, Block 1)
        allegiance_data = read_block(_reader, 39, 1)
        allegiance = hex_to_text(allegiance_data) if allegiance_data else 'Unknown'
        
        # Determine faction
        faction = f"faction{uid[0] % 31 + 1}"
        
        # Halt the card
        _reader.MFRC522_StopCrypto1()
        
        data = {
            "role": role,
            "name": name,
            "allegiance": allegiance,
            "neoId": neo_id,
            "faction": faction
        }
        
        log_rfid_scan(data)
        return data
                
    except Exception as e:
        log(f"Error reading RFID: {e}")
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
            # Scan for cards
            log("Scanning for RFID tags...")
            if timeout:
                log(f"Timeout set to {timeout} seconds")
                
            data = scan_rfid()
            
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
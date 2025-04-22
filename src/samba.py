#!/usr/bin/env python3
"""
Samba file sharing functionality for the Alleycat Photobooth.
"""

import os
from smb.SMBConnection import SMBConnection
from logit import log
from settings import load_settings

def copy_to_samba(local_file):
    """Copy a local file to the Samba share"""
    if not os.path.exists(local_file):
        log(f"Local file does not exist: {local_file}")
        return False
        
    settings = load_settings()
    samba_share = settings.get("samba_share", "")
    if not samba_share:
        log("No Samba share configured")
        return False
    
    try:
        # Parse the share URL (format: smb://server:port/share)
        parts = samba_share.replace('smb://', '').split('/')
        if len(parts) < 2:
            log("Invalid Samba share format")
            return False
            
        server_port = parts[0].split(':')
        server = server_port[0]
        port = int(server_port[1]) if len(server_port) > 1 else 445
        share = parts[1]
        
        # Create SMB connection
        conn = SMBConnection(
            settings.get('samba_username', 'guest'),
            settings.get('samba_password', ''),
            'alleycat-photobooth',
            server,
            use_ntlm_v2=True
        )
        
        # Connect and copy file
        if not conn.connect(server, port):
            log("Failed to connect to Samba server")
            return False
            
        with open(local_file, 'rb') as file:
            filename = os.path.basename(local_file)
            conn.storeFile(share, filename, file)
            
        log(f"Successfully copied {filename} to Samba share")
        return True
        
    except Exception as e:
        log(f"Error copying to Samba share: {e}")
        return False
    finally:
        try:
            conn.close()
        except:
            pass
#!/bin/bash

# RUN SETUP_USB_RAID.SH FIRST

# Create video directories
sudo mkdir -p /mnt/usbdata/video/in
sudo mkdir -p /mnt/usbdata/video/proc
sudo mkdir -p /mnt/usbdata/video/out

cp ./settings.json.example /mnt/usbdata/settings.json
#!/bin/bash

DEVICE="/dev/video0"
OUTPUT="webcam_info.txt"
REQUIRED_PKGS=("v4l-utils" "ffmpeg")
INSTALL_PKGS=()

# Step 1–2: Check for required packages
echo "Checking required packages..."
for pkg in "${REQUIRED_PKGS[@]}"; do
    if ! dpkg -s "$pkg" &> /dev/null; then
        echo "Missing: $pkg"
        INSTALL_PKGS+=("$pkg")
    else
        echo "Found: $pkg"
    fi
done

# Step 3: Install missing packages
if [ ${#INSTALL_PKGS[@]} -gt 0 ]; then
    echo "Installing missing packages: ${INSTALL_PKGS[*]}"
    sudo apt update
    sudo apt install -y "${INSTALL_PKGS[@]}"
fi

# Step 4: Collect info and save to file
echo "Gathering webcam info..."

# Empty file first
echo "Webcam Information Report" > "$OUTPUT"
echo "Generated on: $(date)" >> "$OUTPUT"
echo "-----------------------------------" >> "$OUTPUT"

{
    echo "=== Device Info ==="
    v4l2-ctl --device="$DEVICE" --all

    echo -e "\n=== Supported Formats and Resolutions ==="
    v4l2-ctl --device="$DEVICE" --list-formats-ext

    echo -e "\n=== Adjustable Camera Controls ==="
    v4l2-ctl --device="$DEVICE" --list-ctrls

    echo -e "\n=== FFmpeg Video Capabilities ==="
    ffmpeg -f v4l2 -list_formats all -i "$DEVICE"
} | tee -a "$OUTPUT"

# Step 5: Uninstall only what we installed
if [ ${#INSTALL_PKGS[@]} -gt 0 ]; then
    echo "Cleaning up: removing installed packages: ${INSTALL_PKGS[*]}"
    sudo apt remove -y "${INSTALL_PKGS[@]}"
    sudo apt autoremove -y
else
    echo "No packages needed to be installed, skipping removal."
fi

echo "✅ Done. Info saved to: $OUTPUT"

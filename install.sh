#!/bin/bash
set -e

echo "======================================================="
echo "Example Brand Inventory - macOS/Linux Installer"
echo "======================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.12 or later."
    exit 1
fi

echo "Installing required Python dependencies..."
python3 -m pip install -r requirements.txt --break-system-packages 2>/dev/null || python3 -m pip install -r requirements.txt

echo "Starting the application..."
./start.sh

# Ask user if they want to install it as a system service
OS="$(uname -s)"
if [ "$OS" = "Linux" ]; then
    echo ""
    read -p "Do you want to install Example Brand Inventory as a systemd service to start automatically on boot? (y/n): " INSTALL_SERVICE
    if [[ "$INSTALL_SERVICE" =~ ^[Yy]$ ]]; then
        echo "Installing systemd service..."
        SERVICE_FILE="/etc/systemd/system/example_brand-inventory.service"
        CURRENT_DIR="$(pwd)"

        # Create systemd service file
        sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Example Brand Inventory Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/start.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable example_brand-inventory.service
        echo "Systemd service 'example_brand-inventory' installed and enabled to start on boot."
    fi
fi

echo "======================================================="
echo "Application successfully installed and started!"
echo "You can access it at http://localhost"
echo "======================================================="

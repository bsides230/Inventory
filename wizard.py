import os
import sys
import platform
import subprocess
from pathlib import Path

def print_header(title):
    print("=" * 50)
    print(f" {title.center(48)} ")
    print("=" * 50)

def install_dependencies():
    print_header("DEPENDENCY INSTALLER")
    choice = input("Install required dependencies? (Y/n): ").strip().lower()

    if choice in ['y', 'yes', '']:
        pip_cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        try:
            print("Installing dependencies...")
            subprocess.check_call(pip_cmd)
            print("Dependencies installed successfully.")
        except subprocess.CalledProcessError:
            print("Error installing dependencies.")
            return False
    else:
        print("Skipping dependencies.")
    return True

def configure_port():
    print("\n--- Server Port ---")
    current_port = "8030"
    port_file = Path("port.txt")
    if port_file.exists():
        try:
            current_port = port_file.read_text().strip()
        except:
            pass

    print(f"Current Port: {current_port}")
    choice = input(f"Change Port? (current: {current_port}) (y/N): ").strip().lower()
    if choice in ['y', 'yes']:
        new_port = input("Enter new port number: ").strip()
        if new_port.isdigit():
            try:
                port_file.write_text(new_port)
                print(f"Port updated to {new_port}.")
            except Exception as e:
                print(f"Error saving port: {e}")
        else:
            print("Invalid port number. Keeping current port.")
    else:
        print("Keeping current port.")

def configure_auth():
    print("\n--- Authentication ---")
    print("Falcone's Pizza Inventory uses username and 4-digit PIN for authentication.")
    print("By default, authentication is ON.")
    print("Run `toggle_auth.py` manually to turn it on/off anytime.")
    print("Or you can toggle it now.")

    auth_enabled = True
    flags_dir = Path("global_flags")
    no_auth_file = flags_dir / "no_auth"

    if no_auth_file.exists():
        auth_enabled = False

    status = "ON (Required)" if auth_enabled else "OFF (Disabled)"
    print(f"Current Status: {status}")

    choice = input("Toggle authentication status? (y/N): ").strip().lower()
    if choice in ['y', 'yes']:
        try:
            subprocess.run([sys.executable, "toggle_auth.py"])
        except Exception as e:
            print(f"Error running toggle_auth.py: {e}")

def start_server():
    print("\n--- Launch ---")
    choice = input("Start Falcone's Server now? (Y/n): ").strip().lower()
    if choice in ['y', 'yes', '']:
        print("\nStarting Server...")
        try:
            subprocess.run([sys.executable, "server.py"])
        except KeyboardInterrupt:
            print("\nServer stopped.")
        except Exception as e:
            print(f"Error starting server: {e}")

def main():
    print_header("FALCONE'S PIZZA WIZARD")

    if not install_dependencies():
        print("Dependency installation failed. Continuing, but app may not work.")
        input("Press Enter to continue...")

    configure_port()
    configure_auth()

    print("\nSetup Complete!")
    start_server()

if __name__ == "__main__":
    main()

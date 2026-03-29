#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
import string
import secrets
import textwrap

# --- Dependency Management ---
REQUIRED_PACKAGES = ["python-dotenv", "rich"]

def install_dependencies():
    print("Checking and installing required Python packages...")
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace('-', '_') if pkg != 'python-dotenv' else 'dotenv')
        except ImportError:
            print(f"Installing {pkg}...")
            # Use --break-system-packages if running system-wide python on PEP 668 environments (like Debian 12+)
            cmd = [sys.executable, "-m", "pip", "install", pkg, "--break-system-packages"]
            try:
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                # Fallback without --break-system-packages
                cmd = [sys.executable, "-m", "pip", "install", pkg]
                subprocess.check_call(cmd)

install_dependencies()

from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()

ENV_FILE = ".env"
SERVICE_FILE = "/etc/systemd/system/falcones-inventory.service"

def generate_secret_key(length=32):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

def check_docker():
    try:
        subprocess.check_output(["docker", "--version"])
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def install_docker():
    console.print("[yellow]Docker is not installed. Attempting to install Docker...[/yellow]")
    if sys.platform == "linux":
        try:
            # Download and run the official convenience script
            subprocess.check_call(["curl", "-fsSL", "https://get.docker.com", "-o", "get-docker.sh"])
            subprocess.check_call(["sudo", "sh", "get-docker.sh"])
            os.remove("get-docker.sh")

            # Add user to docker group
            user = os.environ.get("USER")
            if user:
                subprocess.check_call(["sudo", "usermod", "-aG", "docker", user])
                console.print(f"[green]Added {user} to the docker group. You may need to log out and back in.[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to install Docker: {e}[/red]")
            sys.exit(1)
    else:
        console.print("[red]Unsupported OS for automatic Docker installation. Please install Docker manually.[/red]")
        sys.exit(1)

def setup_env():
    console.print(Panel.fit("Environment Configuration", style="bold blue"))

    if not os.path.exists(ENV_FILE):
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ENV_FILE)
            console.print("[green]Created .env from .env.example[/green]")
        else:
            open(ENV_FILE, 'w').close()
            console.print("[green]Created new .env file[/green]")

    load_dotenv(ENV_FILE)

    # Core Settings
    app_domain = Prompt.ask("Enter your public domain (e.g., falcones.pizza)", default=os.getenv("APP_DOMAIN", "falcones.pizza"))
    app_env = Prompt.ask("Environment", choices=["production", "development"], default=os.getenv("APP_ENV", "production"))

    # JWT Secret
    jwt_secret = os.getenv("AUTH_JWT_SECRET")
    if not jwt_secret or jwt_secret == "change-me":
        jwt_secret = generate_secret_key()
        console.print("[green]Generated a new secure AUTH_JWT_SECRET[/green]")

    # Email / SMTP Settings
    setup_email = Confirm.ask("Do you want to configure SMTP for order emails now?", default=True)

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USERNAME", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    smtp_tls = os.getenv("SMTP_USE_TLS", "true")
    smtp_sender = os.getenv("SMTP_SENDER_EMAIL", f"orders@{app_domain}")

    if setup_email:
        smtp_host = Prompt.ask("SMTP Host", default=smtp_host)
        smtp_port = Prompt.ask("SMTP Port", default=smtp_port)
        smtp_user = Prompt.ask("SMTP Username", default=smtp_user)
        smtp_pass = Prompt.ask("SMTP Password", default=smtp_pass, password=True)
        smtp_tls = Prompt.ask("Use TLS?", choices=["true", "false"], default=smtp_tls)
        smtp_sender = Prompt.ask("Sender Email", default=smtp_sender)

    # Save to .env
    set_key(ENV_FILE, "APP_DOMAIN", app_domain)
    set_key(ENV_FILE, "APP_ENV", app_env)
    set_key(ENV_FILE, "AUTH_JWT_SECRET", jwt_secret)
    set_key(ENV_FILE, "CORS_ALLOWED_ORIGINS", f"https://{app_domain}")

    if setup_email:
        set_key(ENV_FILE, "SMTP_HOST", smtp_host)
        set_key(ENV_FILE, "SMTP_PORT", smtp_port)
        set_key(ENV_FILE, "SMTP_USERNAME", smtp_user)
        set_key(ENV_FILE, "SMTP_PASSWORD", smtp_pass)
        set_key(ENV_FILE, "SMTP_USE_TLS", smtp_tls)
        set_key(ENV_FILE, "SMTP_SENDER_EMAIL", smtp_sender)

    # Ensure some necessary production defaults if not present
    if not os.getenv("DATABASE_URL"):
        set_key(ENV_FILE, "DATABASE_URL", "postgresql+psycopg2://inventory:inventory@db:5432/inventory")

    console.print(f"[green]Environment configuration saved to {ENV_FILE}[/green]\n")

def setup_systemd():
    console.print(Panel.fit("System Service Configuration", style="bold blue"))
    if sys.platform != "linux":
        console.print("[yellow]Systemd setup is only supported on Linux.[/yellow]\n")
        return

    install_service = Confirm.ask("Do you want to install Falcones Pizza Inventory as a systemd service (auto-start on boot)?", default=True)

    if install_service:
        current_dir = os.path.abspath(os.getcwd())
        service_content = textwrap.dedent(f"""\
            [Unit]
            Description=Falcones Pizza Inventory Service
            Requires=docker.service
            After=docker.service

            [Service]
            Type=oneshot
            RemainAfterExit=yes
            WorkingDirectory={current_dir}
            ExecStart=/usr/bin/docker compose up -d
            ExecStop=/usr/bin/docker compose down

            [Install]
            WantedBy=multi-user.target
        """)

        try:
            # Create a temporary file and sudo cp it
            tmp_service = "/tmp/falcones-inventory.service"
            with open(tmp_service, "w") as f:
                f.write(service_content)

            subprocess.check_call(["sudo", "cp", tmp_service, SERVICE_FILE])
            subprocess.check_call(["sudo", "systemctl", "daemon-reload"])
            subprocess.check_call(["sudo", "systemctl", "enable", "falcones-inventory.service"])
            os.remove(tmp_service)
            console.print("[green]Systemd service installed and enabled successfully.[/green]\n")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to setup systemd service: {e}[/red]\n")

def start_application():
    console.print(Panel.fit("Starting Application", style="bold blue"))
    try:
        console.print("[yellow]Building and starting Docker containers (this may take a minute)...[/yellow]")
        subprocess.check_call(["docker", "compose", "up", "-d", "--build"])
        console.print("[green]Application started successfully![/green]")

        app_domain = os.getenv("APP_DOMAIN", "localhost")
        protocol = "https" if app_domain != "localhost" else "http"
        console.print(f"\n[bold green]You can now access your application at: {protocol}://{app_domain}[/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to start application: {e}[/red]")

def main():
    console.print(Panel.fit("Falcones Pizza Inventory Deployment Wizard", style="bold green"))

    if not check_docker():
        install_docker()
    else:
        console.print("[green]Docker is installed.[/green]")

    # Check if docker daemon is running
    try:
        subprocess.check_output(["docker", "info"], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        console.print("[red]Docker daemon is not running. Please start Docker and try again.[/red]")
        sys.exit(1)

    setup_env()
    setup_systemd()
    start_application()

if __name__ == "__main__":
    # Ensure we run in the directory where the script is located
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()

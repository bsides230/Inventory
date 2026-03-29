import os
from pathlib import Path

def main():
    flags_dir = Path("global_flags")
    flags_dir.mkdir(exist_ok=True)

    flag_file = flags_dir / "no_auth"

    print("--- Falcone's Inventory Authentication Toggle ---")

    if flag_file.exists():
        try:
            flag_file.unlink()
            print("\n[SECURE] Authentication ENABLED.")
            print("System will require a valid username and PIN.")
        except Exception as e:
            print(f"Error removing flag: {e}")
    else:
        try:
            flag_file.touch()
            print("\n[OPEN] Authentication DISABLED.")
            print("System is now open. No login required.")
            print("WARNING: Ensure this port is not exposed to the public internet.")
        except Exception as e:
            print(f"Error creating flag: {e}")

    print("\n-------------------------------------------------")

if __name__ == "__main__":
    main()

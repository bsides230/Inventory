import sys
import json
from pathlib import Path

def check_integrity():
    orders_dir = Path("orders/submitted")
    drafts_dir = Path("drafts")
    flags_dir = Path("orders/flags")

    issues = []

    # Check drafts
    if drafts_dir.exists():
        for draft_file in drafts_dir.glob("*.json"):
            try:
                with open(draft_file, 'r') as f:
                    data = json.load(f)
                    if "version" not in data:
                        issues.append(f"Draft {draft_file.name} missing 'version' for optimistic concurrency")
                    if "state" not in data and "status" not in data:
                        issues.append(f"Draft {draft_file.name} missing 'state' or 'status'")
            except Exception as e:
                issues.append(f"Error reading draft {draft_file.name}: {e}")

    # Check orders
    if orders_dir.exists():
        for order_file in orders_dir.glob("*.json"):
            try:
                with open(order_file, 'r') as f:
                    data = json.load(f)
                    order_id = data.get("id")
                    if not order_id:
                        issues.append(f"Order {order_file.name} missing 'id'")
                        continue

                    # Check flag
                    flag_file = flags_dir / f"{order_id}.state"
                    if not flag_file.exists():
                        issues.append(f"Order {order_file.name} missing state flag at {flag_file}")
            except Exception as e:
                issues.append(f"Error reading order {order_file.name}: {e}")

    if issues:
        print("Integrity issues found:")
        for issue in issues:
            print(f" - {issue}")
        sys.exit(1)
    else:
        print("Data integrity check passed.")
        sys.exit(0)

if __name__ == "__main__":
    check_integrity()

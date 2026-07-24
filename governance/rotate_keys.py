import argparse
import sys
from governance.keys import KeyManager, AUDIT_LOG_KEY_ENV, SNAPSHOT_KEY_ENV, ZERO_TRUST_KEY_ENV


def rotate_key(key_type: str, dry_run: bool = False) -> str:
    """Rotate a specific key type."""
    key_map = {
        "audit_log": AUDIT_LOG_KEY_ENV,
        "snapshot": SNAPSHOT_KEY_ENV,
        "zero_trust": ZERO_TRUST_KEY_ENV,
    }
    
    if key_type not in key_map:
        raise ValueError(f"Unknown key type: {key_type}. Valid types: {', '.join(key_map.keys())}")
    
    env_var = key_map[key_type]
    manager = KeyManager()
    
    if dry_run:
        print(f"[DRY RUN] Would rotate key: {env_var}")
        return "dry_run_key"
    
    old_key = manager.get_key(env_var)
    new_key = manager.rotate_key(env_var)
    
    print(f"Rotated key: {env_var}")
    print(f"Old key (first 8 chars): {old_key[:8]}...")
    print(f"New key (first 8 chars): {new_key[:8]}...")
    
    return new_key


def rotate_all_keys(dry_run: bool = False):
    """Rotate all keys."""
    key_types = ["audit_log", "snapshot", "zero_trust"]
    
    print("\n" + "=" * 60)
    print("KEY ROTATION")
    print("=" * 60)
    
    if dry_run:
        print("[DRY RUN MODE - No changes will be made]\n")
    
    for key_type in key_types:
        try:
            rotate_key(key_type, dry_run)
            print()
        except Exception as e:
            print(f"Error rotating {key_type}: {e}\n")
    
    print("=" * 60)
    
    if not dry_run:
        print("\nNext steps:")
        print("1. Restart the council system to use new keys")
        print("2. Verify audit log integrity:")
        print("   python -c \"from governance.audit_log import verify_log_integrity; verify_log_integrity()\"")
        print("3. Verify snapshot integrity:")
        print("   python -c \"from core.snapshots import verify_snapshot_chain; verify_snapshot_chain('test_node')\"")
        print("4. Document rotation in session_log.md")


def main():
    parser = argparse.ArgumentParser(
        description="Rotate HMAC keys for the Autonomous 3-Agent Council",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m governance.rotate_keys --all
  python -m governance.rotate_keys --key audit_log
  python -m governance.rotate_keys --all --dry-run
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Rotate all keys"
    )
    group.add_argument(
        "--key",
        type=str,
        choices=["audit_log", "snapshot", "zero_trust"],
        help="Rotate specific key type"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview rotation without making changes"
    )
    
    args = parser.parse_args()
    
    try:
        if args.all:
            rotate_all_keys(dry_run=args.dry_run)
        else:
            rotate_key(args.key, dry_run=args.dry_run)
        
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

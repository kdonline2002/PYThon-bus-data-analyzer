from pathlib import Path
import shutil
from datetime import datetime
import re
import streamlit as st

def cleanup_old_backups(backup_dir: Path, folder_name: str, keep: int = 7):
    # Find all backups for this folder (logic still works as description is at the end)
    backups = sorted(
        [p for p in backup_dir.iterdir() if p.is_dir() and p.name.startswith(folder_name + "_backup_")],
        key=lambda x: x.stat().st_mtime,
        reverse=True  # newest first
    )

    # Delete old ones
    for old_backup in backups[keep:]:
        print(f"🗑️ Deleting old backup: {old_backup.name}")
        shutil.rmtree(old_backup)


def backup_folder(source: Path, destination: Path, keep: int = 7, description: str = ""):
    if not source.exists():
        raise ValueError(f"Source folder does not exist: {source}")

    # Create timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Sanitize and format description
    # Replaces spaces with hyphens and removes non-alphanumeric characters
    clean_desc = ""
    if description:
        # Keep only alphanumeric, hyphens, and underscores
        clean_desc = re.sub(r'[^\w\s-]', '', description).strip().replace(' ', '-')
        clean_desc = f"_{clean_desc}"

    # Create backup folder name: folder_backup_timestamp_description
    backup_name = f"{source.name}_backup_{timestamp}{clean_desc}"
    backup_path = destination / backup_name

    print(f"📦 Backing up:\n{source} → {backup_path}")

    # Copy folder
    shutil.copytree(source, backup_path)

    print("✅ Backup completed!")

    # Cleanup old backups
    cleanup_old_backups(destination, source.name, keep)


def main():
    # source_folder = Path.home() / input("Source directory: ").strip()
    # backup_location = Path.home() / input("Backup root directory: ").strip()
    source_folder = Path.home() / "PYThon bus-data-analyzer"
    backup_location = Path.home() / "PYThon bus-data-analyzer_backups"
    # backup_location = Path.home() / "OneDrive/Desktop/CAR"
    backup_location.mkdir(exist_ok=True, parents=True)
    # Option 1: Hardcoded description
    # backup_folder(source_folder, backup_location, keep=5, description="added-new-feature")
    # Option 2: Ask user for description
    user_desc = input("Enter a short description (optional, press Enter to skip): ").strip()
    
    backup_folder(source_folder, backup_location, keep=7, description=user_desc)


if __name__ == "__main__":
    main()
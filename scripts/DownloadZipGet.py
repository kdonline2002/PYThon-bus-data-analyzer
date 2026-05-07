from pathlib import Path
import shutil
import zipfile
import sys


# -----------------------------
# Config
# -----------------------------
DOWNLOADS = Path.home() / "Downloads"
DEST_FOLDER = Path.home() / "PYTHON bus-data-analyzer Otter"


# -----------------------------
# Helpers
# -----------------------------
def get_latest_zip(folder: Path):
    zip_files = list(folder.glob("*.zip"))

    if not zip_files:
        raise FileNotFoundError("No zip files found in Downloads.")

    # newest by modified time
    latest = max(zip_files, key=lambda f: f.stat().st_mtime)
    return latest


def main():
    try:
        latest_zip = get_latest_zip(DOWNLOADS)

        print(f"Latest zip found: {latest_zip.name}")

        # Create destination folder
        DEST_FOLDER.mkdir(parents=True, exist_ok=True)

        # Copy zip into destination
        copied_zip = DEST_FOLDER / latest_zip.name
        shutil.copy2(latest_zip, copied_zip)

        print(f"Copied to: {copied_zip}")

        # Optional:
        # remove previous extracted contents (except zip)
        for item in DEST_FOLDER.iterdir():
            if item == copied_zip:
                continue

            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        # Unzip
        with zipfile.ZipFile(copied_zip, "r") as z:
            z.extractall(DEST_FOLDER)

        print(f"Unzipped into: {DEST_FOLDER}")
        print("Done.")

    except Exception as e:
        print("Error:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
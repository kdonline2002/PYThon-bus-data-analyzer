from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROFILE_SCHEMA_VERSION = 1
DEFAULT_PROFILE_DIR = Path("mapping_profiles")


@dataclass
class MappingProfile:
    """Saved column mappings for one recurring workbook/export format."""

    name: str
    main_mapping: dict[str, str] = field(default_factory=dict)
    customer_mapping: dict[str, str] = field(default_factory=dict)
    product_mapping: dict[str, str] = field(default_factory=dict)
    main_dataset_type: str | None = None
    schema_version: int = PROFILE_SCHEMA_VERSION
    created_at: str | None = None
    updated_at: str | None = None


def sanitize_profile_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_. -]+", "", str(name)).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:80]


def _profile_path(name: str, profile_dir: Path = DEFAULT_PROFILE_DIR) -> Path:
    safe_name = sanitize_profile_name(name)
    if not safe_name:
        raise ValueError("Profile name cannot be empty.")
    return profile_dir / f"{safe_name}.json"


def ensure_profile_dir(profile_dir: Path = DEFAULT_PROFILE_DIR) -> Path:
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir


def list_mapping_profiles(profile_dir: Path = DEFAULT_PROFILE_DIR) -> list[str]:
    if not profile_dir.exists():
        return []
    return sorted(path.stem for path in profile_dir.glob("*.json") if path.is_file())


def _clean_mapping(mapping: dict[str, Any] | None) -> dict[str, str]:
    if not mapping:
        return {}
    return {str(k): str(v) for k, v in mapping.items() if k and v}


def save_mapping_profile(profile: MappingProfile, profile_dir: Path = DEFAULT_PROFILE_DIR) -> Path:
    ensure_profile_dir(profile_dir)

    now = datetime.now(timezone.utc).isoformat()
    path = _profile_path(profile.name, profile_dir)

    existing_created_at = None
    if path.exists():
        try:
            existing_created_at = json.loads(path.read_text(encoding="utf-8")).get("created_at")
        except json.JSONDecodeError:
            existing_created_at = None

    profile.name = sanitize_profile_name(profile.name)
    profile.schema_version = PROFILE_SCHEMA_VERSION
    profile.created_at = existing_created_at or profile.created_at or now
    profile.updated_at = now
    profile.main_mapping = _clean_mapping(profile.main_mapping)
    profile.customer_mapping = _clean_mapping(profile.customer_mapping)
    profile.product_mapping = _clean_mapping(profile.product_mapping)

    path.write_text(json.dumps(asdict(profile), indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_mapping_profile(name: str, profile_dir: Path = DEFAULT_PROFILE_DIR) -> MappingProfile:
    path = _profile_path(name, profile_dir)
    if not path.exists():
        raise FileNotFoundError(f"Mapping profile not found: {name}")

    data = json.loads(path.read_text(encoding="utf-8"))
    schema_version = int(data.get("schema_version", 0))
    if schema_version != PROFILE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported mapping profile schema version {schema_version}. "
            f"Expected {PROFILE_SCHEMA_VERSION}."
        )

    return MappingProfile(
        name=str(data.get("name") or sanitize_profile_name(name)),
        main_mapping=_clean_mapping(data.get("main_mapping")),
        customer_mapping=_clean_mapping(data.get("customer_mapping")),
        product_mapping=_clean_mapping(data.get("product_mapping")),
        main_dataset_type=data.get("main_dataset_type"),
        schema_version=schema_version,
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )

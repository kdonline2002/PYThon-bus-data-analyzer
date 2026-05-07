from __future__ import annotations

import json

import pytest

from utils.mapping_profiles import (
    MappingProfile,
    list_mapping_profiles,
    load_mapping_profile,
    sanitize_profile_name,
    save_mapping_profile,
)


def test_sanitize_profile_name_removes_unsafe_characters_and_normalizes_spaces() -> None:
    assert sanitize_profile_name(" Monthly Sales / Export?! ") == "Monthly_Sales_Export"


def test_save_and_load_mapping_profile_round_trip(tmp_path) -> None:
    profile = MappingProfile(
        name="monthly sales export",
        main_dataset_type="sales",
        main_mapping={"Order Date": "date", "Revenue": "sales_amount", "": "ignored"},
        customer_mapping={"Client ID": "customer_id"},
        product_mapping={"Item Code": "sku"},
    )

    saved_path = save_mapping_profile(profile, profile_dir=tmp_path)
    loaded = load_mapping_profile("monthly sales export", profile_dir=tmp_path)

    assert saved_path == tmp_path / "monthly_sales_export.json"
    assert loaded.name == "monthly_sales_export"
    assert loaded.main_dataset_type == "sales"
    assert loaded.main_mapping == {"Order Date": "date", "Revenue": "sales_amount"}
    assert loaded.customer_mapping == {"Client ID": "customer_id"}
    assert loaded.product_mapping == {"Item Code": "sku"}
    assert loaded.created_at is not None
    assert loaded.updated_at is not None


def test_list_mapping_profiles_returns_sorted_profile_names(tmp_path) -> None:
    save_mapping_profile(MappingProfile(name="z profile"), profile_dir=tmp_path)
    save_mapping_profile(MappingProfile(name="a profile"), profile_dir=tmp_path)

    assert list_mapping_profiles(profile_dir=tmp_path) == ["a_profile", "z_profile"]


def test_save_existing_profile_preserves_created_at_and_updates_content(tmp_path) -> None:
    first_path = save_mapping_profile(
        MappingProfile(name="repeat", main_mapping={"A": "date"}),
        profile_dir=tmp_path,
    )
    first_created_at = json.loads(first_path.read_text(encoding="utf-8"))["created_at"]

    save_mapping_profile(
        MappingProfile(name="repeat", main_mapping={"B": "quantity"}),
        profile_dir=tmp_path,
    )
    loaded = load_mapping_profile("repeat", profile_dir=tmp_path)

    assert loaded.created_at == first_created_at
    assert loaded.main_mapping == {"B": "quantity"}


def test_load_missing_profile_raises_file_not_found(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_mapping_profile("missing", profile_dir=tmp_path)


def test_load_unsupported_schema_version_raises_value_error(tmp_path) -> None:
    bad_profile = tmp_path / "bad.json"
    bad_profile.write_text(json.dumps({"schema_version": 999, "name": "bad"}), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported mapping profile schema version"):
        load_mapping_profile("bad", profile_dir=tmp_path)

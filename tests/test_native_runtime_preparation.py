from copy import deepcopy

import pytest

from scripts.prepare_native_runtime import prepare


def staging():
    return {"native_billing": {
        provider: {identity: "art.lazying.westicker", "purchase_enabled": False,
                   "purchase_user_ids": [], "sandbox_user_ids": [],
                   "notifications_enabled": True,
                   "products": {(f"art.lazying.westicker.{p}.monthly" if provider == "apple"
                                 else f"westicker_{p}_monthly"): p
                                for p in ("pocket", "creator", "studio")}}
        for provider, identity in (("apple", "bundle_id"), ("google", "package"))}}


def test_native_merge_preserves_web_sales_identity_and_generation():
    before = {"stripe_purchase_enabled": True, "stripe_key": "fixture", "providers": {"test": {}},
              "animation_enabled": False, "state": "/private/fixture"}
    snapshot = deepcopy(before)
    merged = prepare(before, staging())
    assert before == snapshot
    assert {k: v for k, v in merged.items() if k != "native_billing"} == before
    assert merged["native_billing"]["apple"]["notifications_enabled"]


@pytest.mark.parametrize("key,value", [("purchase_enabled", True),
    ("purchase_user_ids", ["test-owner"]), ("sandbox_user_ids", ["test-owner"]),
    ("bundle_id", "other.app"), ("products", {})])
def test_native_staging_refuses_unqualified_activation(key, value):
    native = staging()
    native["native_billing"]["apple"][key] = value
    with pytest.raises(ValueError):
        prepare({}, native)


def test_native_merge_refuses_cross_scope_or_active_rollout_overwrite():
    with pytest.raises(ValueError):
        prepare({}, staging() | {"stripe_purchase_enabled": False})
    with pytest.raises(ValueError):
        prepare({"native_billing": {"google": {"purchase_user_ids": ["owner"]}}}, staging())

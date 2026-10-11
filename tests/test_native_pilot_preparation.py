from copy import deepcopy

import pytest

from scripts.prepare_native_pilot import prepare
from test_native_runtime_preparation import staging


OWNER = "a" * 32


def setup(provider="apple"):
    current = staging() | {"stripe_purchase_enabled": True, "identity": "retained"}
    candidate = staging()
    candidate["native_billing"][provider].update(
        purchase_enabled=True, accept_sandbox=True,
        purchase_user_ids=[OWNER], sandbox_user_ids=[OWNER])
    return current, candidate


@pytest.mark.parametrize("provider", ["apple", "google"])
def test_pilot_only_merges_selected_four_fields(provider):
    current, candidate = setup(provider)
    snapshot = deepcopy(current)
    other = "google" if provider == "apple" else "apple"
    candidate["native_billing"][other]["notifications_enabled"] = False
    result = prepare(current, candidate, provider, OWNER)
    assert current == snapshot
    assert result["identity"] == current["identity"]
    assert result["stripe_purchase_enabled"]
    assert result["native_billing"][other] == current["native_billing"][other]
    assert result["native_billing"][provider]["purchase_user_ids"] == [OWNER]
    assert prepare(result, candidate, provider, OWNER) == result


@pytest.mark.parametrize("field,value", [
    ("purchase_enabled", False), ("purchase_enabled", 1),
    ("accept_sandbox", False), ("purchase_user_ids", []),
    ("purchase_user_ids", [OWNER, "b" * 32]), ("sandbox_user_ids", []),
    ("bundle_id", "another.app"), ("products", {}),
    ("notifications_enabled", False),
])
def test_pilot_refuses_broadened_or_changed_configuration(field, value):
    current, candidate = setup()
    candidate["native_billing"]["apple"][field] = value
    with pytest.raises(ValueError):
        prepare(current, candidate, "apple", OWNER)


def test_pilot_preserves_old_sandbox_lineage_and_other_rollout():
    current, candidate = setup()
    current["native_billing"]["apple"]["sandbox_user_ids"] = ["b" * 32]
    current["native_billing"]["google"].update(purchase_enabled=True, purchase_user_ids=["c" * 32])
    result = prepare(current, candidate, "apple", OWNER)
    assert result["native_billing"]["apple"]["sandbox_user_ids"] == ["b" * 32, OWNER]
    assert result["native_billing"]["google"] == current["native_billing"]["google"]


def test_pilot_refuses_replacing_existing_purchase_audience():
    current, candidate = setup()
    current["native_billing"]["apple"].update(purchase_enabled=True, purchase_user_ids=[])
    with pytest.raises(ValueError):
        prepare(current, candidate, "apple", OWNER)
    current["native_billing"]["apple"].update(purchase_enabled=False, purchase_user_ids=["b" * 32])
    with pytest.raises(ValueError):
        prepare(current, candidate, "apple", OWNER)
    with pytest.raises(ValueError):
        prepare({}, candidate, "apple", OWNER)
    with pytest.raises(ValueError):
        prepare(current, candidate | {"stripe_purchase_enabled": False}, "apple", OWNER)

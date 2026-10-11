"""Catalog unit fixtures are not store receipts or payment qualification."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("google_catalog", Path(__file__).parents[1] / "scripts/provision_google_subscriptions.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class API:
    def __init__(self):
        self.products = {}
        self.writes = []
        self.conversions = 0

    def call(self, path, *, method="GET", data=None, params=None):
        if path == "/pricing:convertRegionPrices":
            self.conversions += 1
            return {"regionVersion": {"version": "fixture"}}
        if method == "GET":
            if path not in self.products:
                raise catalog.ProviderError(404)
            return deepcopy(self.products[path])
        self.writes.append((method, path, params, deepcopy(data)))
        if path.endswith("/basePlans/monthly:activate"):
            product = self.products[path.removesuffix("/basePlans/monthly:activate")]
            product["basePlans"][0]["state"] = "ACTIVE"
            return deepcopy(product)
        product = deepcopy(data)
        product["basePlans"][0]["state"] = "DRAFT"
        self.products["/subscriptions/" + product["productId"]] = product
        return product


def test_provision_drafts_then_read_only_rerun(tmp_path):
    api = API()
    receipt = catalog.provision(api, tmp_path, apply=True)
    assert len(api.writes) == 3
    assert [p["usd_cents"] for p in receipt["products"]] == [99, 999, 2499]
    assert all(p["state"] == "DRAFT" for p in receipt["products"])
    assert not receipt["backend_sales_changed"] and receipt["purchases"] == 0
    catalog.provision(api, tmp_path)
    assert len(api.writes) == 3


def test_add_base_plan_without_overwriting_metadata(tmp_path):
    api = API()
    plan = catalog.PLANS[0]
    before = catalog.draft(plan)
    before.pop("basePlans")
    before["listings"][0]["title"] = "Existing approved title"
    api.products["/subscriptions/" + before["productId"]] = before
    catalog.provision(api, tmp_path, apply=True)
    method, _, params, data = api.writes[0]
    assert method == "PATCH" and params["updateMask"] == "basePlans"
    assert data["listings"] == before["listings"]
    assert data["taxAndComplianceSettings"] == before["taxAndComplianceSettings"]


@pytest.mark.parametrize("change", ["active", "price", "period", "region"])
def test_preserves_nonmatching_existing_catalog(tmp_path, change):
    api = API()
    product = catalog.draft(catalog.PLANS[0])
    base = product["basePlans"][0]
    base["state"] = "DRAFT"
    if change == "active":
        base["state"] = "ACTIVE"
    elif change == "price":
        base["regionalConfigs"][0]["price"] = catalog.money(199)
    elif change == "period":
        base["autoRenewingBasePlanType"]["billingPeriodDuration"] = "P1Y"
    else:
        base["regionalConfigs"][0]["regionCode"] = "CA"
    api.products["/subscriptions/" + product["productId"]] = product
    with pytest.raises(ValueError):
        catalog.provision(api, tmp_path, apply=True)
    assert api.writes == []


def test_uncertain_creation_does_not_repeat(tmp_path):
    (tmp_path / "pocket-intent.json").write_text("{}")
    api = API()
    with pytest.raises(ValueError, match="Unresolved"):
        catalog.provision(api, tmp_path, apply=True)
    assert api.writes == []


def test_read_only_mode_never_creates(tmp_path):
    api = API()
    with pytest.raises(ValueError, match="Missing"):
        catalog.provision(api, tmp_path)
    assert api.writes == []


def test_observed_region_version_avoids_account_wide_conversion(tmp_path):
    api = API()
    catalog.provision(api, tmp_path, apply=True, regions_version="2026/01")
    assert api.conversions == 0
    assert all(write[2]["regionsVersion.version"] == "2026/01" for write in api.writes)


def test_invalid_region_version_does_not_write(tmp_path):
    api = API()
    with pytest.raises(ValueError, match="supported-locations"):
        catalog.provision(api, tmp_path, apply=True, regions_version="current")
    assert api.conversions == 0 and api.writes == []


def test_explicit_activation_validates_then_reconciles_without_repeating(tmp_path):
    api = API()
    receipt = catalog.provision(api, tmp_path, apply=True, activate=True)
    assert [p["state"] for p in receipt["products"]] == ["ACTIVE"] * 3
    assert not receipt["backend_sales_changed"] and receipt["purchases"] == 0
    assert len(api.writes) == 6
    catalog.provision(api, tmp_path, apply=True, activate=True)
    assert len(api.writes) == 6


def test_activation_does_not_bypass_read_only_or_unresolved_intent(tmp_path):
    api = API()
    catalog.provision(api, tmp_path, apply=True)
    with pytest.raises(ValueError, match="requires"):
        catalog.provision(api, tmp_path, activate=True)
    (tmp_path / "pocket-activation-intent.json").write_text("{}")
    with pytest.raises(ValueError, match="Unresolved activation"):
        catalog.provision(api, tmp_path, apply=True, activate=True)
    assert len(api.writes) == 3


def test_activation_rejects_wrong_price_before_writing(tmp_path):
    api = API()
    catalog.provision(api, tmp_path, apply=True)
    api.products["/subscriptions/westicker_pocket_monthly"]["basePlans"][0]["regionalConfigs"][0]["price"] = catalog.money(199)
    with pytest.raises(ValueError, match="price"):
        catalog.provision(api, tmp_path, apply=True, activate=True)
    assert len(api.writes) == 3

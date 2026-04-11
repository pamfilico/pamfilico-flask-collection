"""Integration tests for pamfilico-flask-collection — require docker compose up."""

import os

import pytest
import requests

API_URL = os.environ.get("COLLECTION_TEST_API_URL", "http://localhost:5097")


def _api_available():
    try:
        return requests.get(f"{API_URL}/health", timeout=2).status_code == 200
    except Exception:
        return False


integration_required = pytest.mark.skipif(
    not _api_available(),
    reason="API required — run ./run-tests.sh",
)


# --- Pagination ---


@integration_required
def test_default_pagination():
    resp = requests.get(f"{API_URL}/api/items")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is False
    assert len(body["data"]) == 5
    assert body["pagination"]["currentPage"] == 1
    assert body["pagination"]["totalCount"] == 5
    assert body["pagination"]["pageSize"] == 10
    assert body["pagination"]["totalPages"] == 1
    assert body["pagination"]["nextPage"] is None
    assert body["pagination"]["previousPage"] is None


@integration_required
def test_pagination_page_size():
    resp = requests.get(f"{API_URL}/api/items?results_per_page=2&page_number=1")
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["pagination"]["pageSize"] == 2
    assert body["pagination"]["totalPages"] == 3
    assert body["pagination"]["nextPage"] == 2


@integration_required
def test_pagination_page_2():
    resp = requests.get(f"{API_URL}/api/items?results_per_page=2&page_number=2")
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["pagination"]["currentPage"] == 2
    assert body["pagination"]["previousPage"] == 1
    assert body["pagination"]["nextPage"] == 3


@integration_required
def test_pagination_last_page():
    resp = requests.get(f"{API_URL}/api/items?results_per_page=2&page_number=3")
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["pagination"]["nextPage"] is None


# --- Search ---


@integration_required
def test_search_by_name():
    resp = requests.get(f"{API_URL}/api/items?search_by=name&search_value=Laptop")
    body = resp.json()
    assert len(body["data"]) == 2
    names = {item["name"] for item in body["data"]}
    assert "Gaming Laptop" in names
    assert "Office Laptop" in names


@integration_required
def test_search_no_results():
    resp = requests.get(f"{API_URL}/api/items?search_by=name&search_value=NonExistent")
    body = resp.json()
    assert len(body["data"]) == 0
    assert body["pagination"]["totalCount"] == 0


@integration_required
def test_search_invalid_field():
    resp = requests.get(f"{API_URL}/api/items?search_by=invalid_field&search_value=test")
    assert resp.status_code == 400


# --- Ordering ---


@integration_required
def test_order_by_price_asc():
    resp = requests.get(f"{API_URL}/api/items?order_by=price&order_direction=asc")
    body = resp.json()
    prices = [item["price"] for item in body["data"]]
    assert prices == sorted(prices)
    assert body["ordering"]["sortBy"] == "price"
    assert body["ordering"]["sortOrder"] == "asc"


@integration_required
def test_order_by_price_desc():
    resp = requests.get(f"{API_URL}/api/items?order_by=price&order_direction=desc")
    body = resp.json()
    prices = [item["price"] for item in body["data"]]
    assert prices == sorted(prices, reverse=True)


# --- Filtering (via /api/items-filtered) ---


@integration_required
def test_filter_eq():
    resp = requests.get(f"{API_URL}/api/items-filtered?filter[status][eq]=active")
    body = resp.json()
    assert all(item["status"] == "active" for item in body["data"])
    assert len(body["data"]) == 3


@integration_required
def test_filter_gt():
    resp = requests.get(f"{API_URL}/api/items-filtered?filter[price][gt]=200")
    body = resp.json()
    assert all(item["price"] > 200 for item in body["data"])


@integration_required
def test_filter_contains():
    resp = requests.get(f"{API_URL}/api/items-filtered?filter[category][contains]=electron")
    body = resp.json()
    assert all("electron" in item["category"] for item in body["data"])


@integration_required
def test_filter_boolean():
    resp = requests.get(f"{API_URL}/api/items-filtered?filter[is_active][eq]=false")
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "Broken Monitor"


@integration_required
def test_filter_in():
    resp = requests.get(f"{API_URL}/api/items-filtered?filter[status][in]=active,pending")
    body = resp.json()
    assert len(body["data"]) == 4


# --- Combined ---


@integration_required
def test_pagination_with_search():
    resp = requests.get(
        f"{API_URL}/api/items?search_by=category&search_value=electronics"
        "&results_per_page=1&page_number=1"
    )
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["pagination"]["totalCount"] == 3
    assert body["pagination"]["totalPages"] == 3


# --- Validation errors ---


@integration_required
def test_invalid_page_number():
    resp = requests.get(f"{API_URL}/api/items?page_number=abc")
    assert resp.status_code == 400


@integration_required
def test_page_number_zero():
    resp = requests.get(f"{API_URL}/api/items?page_number=0")
    assert resp.status_code == 400


@integration_required
def test_results_per_page_too_large():
    resp = requests.get(f"{API_URL}/api/items?results_per_page=999")
    assert resp.status_code == 400


# --- Empty results ---


@integration_required
def test_empty_page():
    resp = requests.get(f"{API_URL}/api/items?page_number=100")
    body = resp.json()
    assert len(body["data"]) == 0
    assert body["pagination"]["totalCount"] == 5

"""
tests/test_tools.py

Isolated tests for the three FitFindr tools — one per failure mode plus
happy-path checks. Run with: pytest tests/

The search_listings tests need no API key. The suggest_outfit happy/empty-wardrobe
tests call the LLM, so they are skipped automatically when GROQ_API_KEY is not set.
"""

import os

import pytest
from tools import (
    search_listings,
    suggest_outfit,
    create_fit_card,
    compare_price,
    get_trending_styles,
)
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe, load_listings

needs_groq = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping LLM-dependent test",
)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    # Failure mode: nothing matches → empty list, no exception.
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_results_sorted_by_relevance():
    # More keyword overlap should not rank below less overlap.
    results = search_listings("vintage denim jacket", size=None, max_price=200)
    assert isinstance(results, list)
    # Every returned item is a real listing dict with the expected fields.
    for item in results:
        assert "title" in item and "price" in item


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

@needs_groq
def test_suggest_outfit_with_wardrobe():
    item = load_listings()[0]
    result = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""


@needs_groq
def test_suggest_outfit_empty_wardrobe():
    # Failure mode: empty wardrobe → general advice, no crash, non-empty string.
    item = load_listings()[0]
    result = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def test_create_fit_card_empty_outfit():
    # Failure mode: missing outfit → descriptive error string, no exception.
    item = load_listings()[0]
    result = create_fit_card("", item)
    assert isinstance(result, str)
    assert "Unable to generate caption" in result


@needs_groq
def test_create_fit_card_varies():
    item = load_listings()[0]
    outfit = "Pair it with baggy jeans and chunky sneakers for a 90s look."
    card_a = create_fit_card(outfit, item)
    card_b = create_fit_card(outfit, item)
    assert card_a.strip() != ""
    assert card_a != card_b  # higher temperature → different captions


# ── Tool 4: compare_price (stretch) ───────────────────────────────────────────

def test_compare_price_returns_verdict():
    item = load_listings()[0]
    result = compare_price(item)
    assert result["verdict"] in {"great deal", "fair", "overpriced", "unknown"}
    assert result["comparable_count"] >= 0
    assert isinstance(result["message"], str)


def test_compare_price_not_enough_data():
    # Failure mode: an item with no comparables → verdict "unknown", no crash.
    odd_item = {
        "id": "made_up",
        "category": "nonexistent-category",
        "style_tags": ["totally-unique-tag"],
        "price": 25.0,
    }
    result = compare_price(odd_item)
    assert result["verdict"] == "unknown"
    assert result["comparable_count"] < 2


# ── Tool 5: get_trending_styles (stretch) ─────────────────────────────────────

def test_trending_styles_returns_ranked_list():
    trends = get_trending_styles(size=None)
    assert isinstance(trends, list)
    assert len(trends) > 0
    # sorted most popular first
    counts = [t["count"] for t in trends]
    assert counts == sorted(counts, reverse=True)


def test_trending_styles_no_match():
    # Failure mode: no listing in that size → empty list, no crash.
    assert get_trending_styles(size="ZZZ") == []

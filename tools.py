"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Common filler words that shouldn't count as real search terms.
    stopwords = {
        "a", "an", "the", "and", "or", "for", "with", "in", "on", "of", "to",
        "my", "me", "i", "im", "is", "it", "this", "that", "looking", "want",
        "need", "under", "below", "size", "some", "any", "good", "nice",
    }

    # Tokenize the description into clean word-level keywords:
    # strip punctuation, drop stopwords and very short tokens (< 3 chars).
    keywords = [
        re.sub(r"[^a-z0-9]", "", w)
        for w in description.lower().split()
    ]
    keywords = [w for w in keywords if len(w) >= 3 and w not in stopwords]

    scored = []
    for item in listings:
        # --- filter by max_price (inclusive) ---
        if max_price is not None and item["price"] > max_price:
            continue

        # --- filter by size (case-insensitive substring match) ---
        if size is not None and size.lower() not in item["size"].lower():
            continue

        # --- score by keyword overlap with title / description / style_tags ---
        # Match whole words, not raw substrings, so "a" doesn't match everything
        # and "tee" doesn't fire inside "canteen".
        text = " ".join([
            item["title"],
            item["description"],
            " ".join(item["style_tags"]),
            item["category"],
        ]).lower()
        words = set(re.findall(r"[a-z0-9]+", text))
        score = sum(1 for kw in keywords if kw in words)

        # drop listings with no relevant keyword match
        if score == 0:
            continue

        scored.append((score, item))

    # sort by score, highest first; stable sort preserves dataset order on ties
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    item_desc = (
        f"{new_item['title']} — {new_item['description']} "
        f"(category: {new_item['category']}, "
        f"colors: {', '.join(new_item['colors'])}, "
        f"style: {', '.join(new_item['style_tags'])})"
    )

    items = wardrobe.get("items", [])

    if not items:
        # Empty wardrobe (new user): give general styling advice for the item.
        prompt = (
            "You are a friendly personal stylist. A user is considering buying "
            "this secondhand item but hasn't entered any wardrobe yet:\n\n"
            f"{item_desc}\n\n"
            "Give general styling advice for this piece: what kinds of items pair "
            "well with it, what vibe it suits, and how to wear it. 2-3 sentences. "
            "Do not reference specific clothes the user owns, since you don't know them."
        )
    else:
        # Format the wardrobe pieces by name so the LLM can reference them.
        wardrobe_lines = "\n".join(
            f"- {it['name']} ({it['category']})" for it in items
        )
        prompt = (
            "You are a friendly personal stylist. A user is considering buying "
            "this secondhand item:\n\n"
            f"{item_desc}\n\n"
            "Here is what's already in their wardrobe:\n"
            f"{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfit combinations that pair the new item with "
            "specific pieces from their wardrobe (refer to the pieces by name). "
            "Label them 'Outfit 1:' and 'Outfit 2:'. Be concrete about how to wear "
            "each look. Keep each outfit to 1-2 sentences."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Guard: empty or whitespace-only outfit → return an error string, no crash.
    if not outfit or not outfit.strip():
        return "Unable to generate caption: outfit suggestion was empty or missing."

    price = new_item.get("price")
    price_str = f"${price:.0f}" if isinstance(price, (int, float)) else "a steal"

    prompt = (
        "Write a short, casual social media caption (Instagram/TikTok style) for "
        "a thrifted outfit. It should sound like a real OOTD post by an excited "
        "person — NOT a product description.\n\n"
        f"Item: {new_item.get('title', 'this piece')}\n"
        f"Price: {price_str}\n"
        f"Platform: {new_item.get('platform', 'a thrift app')}\n"
        f"Outfit idea: {outfit}\n\n"
        "Requirements: 2-4 sentences. Mention the item name, price, and platform "
        "naturally (once each). Capture the outfit vibe in specific terms. "
        "Casual, lowercase-friendly, emojis okay. Return only the caption."
    )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,  # higher temperature → varied captions for the same input
    )
    return response.choices[0].message.content.strip()


# ── Tool 4: compare_price (stretch) ───────────────────────────────────────────

def compare_price(new_item: dict) -> dict:
    """
    Estimate whether an item's price is fair vs. comparable listings.

    A "comparable" listing is one in the same category that shares at least one
    style tag with the item (and isn't the item itself). The verdict compares the
    item's price to the average price of those comparables.

    Args:
        new_item: The listing dict the user is considering.

    Returns:
        A dict: {verdict, your_price, avg_price, comparable_count, message}.
        verdict is one of "great deal", "fair", "overpriced", or "unknown".
        If fewer than 2 comparables exist, verdict is "unknown" (no crash).
    """
    your_price = new_item.get("price")
    item_tags = set(new_item.get("style_tags", []))
    category = new_item.get("category")

    comparables = [
        listing for listing in load_listings()
        if listing["id"] != new_item.get("id")
        and listing["category"] == category
        and item_tags & set(listing["style_tags"])
    ]

    if len(comparables) < 2 or not isinstance(your_price, (int, float)):
        return {
            "verdict": "unknown",
            "your_price": your_price,
            "avg_price": None,
            "comparable_count": len(comparables),
            "message": "Not enough comparable listings to judge this price.",
        }

    avg_price = sum(c["price"] for c in comparables) / len(comparables)

    if your_price <= avg_price * 0.85:
        verdict = "great deal"
    elif your_price <= avg_price * 1.10:
        verdict = "fair"
    else:
        verdict = "overpriced"

    message = (
        f"${your_price:.0f} is a {verdict} — similar {category} average "
        f"${avg_price:.2f} across {len(comparables)} listings."
    )
    return {
        "verdict": verdict,
        "your_price": float(your_price),
        "avg_price": round(avg_price, 2),
        "comparable_count": len(comparables),
        "message": message,
    }


# ── Tool 5: get_trending_styles (stretch) ─────────────────────────────────────

def get_trending_styles(size: str | None = None, top_n: int = 5) -> list[dict]:
    """
    Surface the most common style tags among listings in the user's size.

    Args:
        size:  Size to filter by (case-insensitive substring), or None for all.
        top_n: How many top styles to return.

    Returns:
        A list of {"style": str, "count": int} dicts, most popular first.
        Returns an empty list if no listings match the given size.
    """
    listings = load_listings()
    if size is not None:
        listings = [
            item for item in listings
            if size.lower() in item["size"].lower()
        ]

    if not listings:
        return []

    counts: dict[str, int] = {}
    for item in listings:
        for tag in item["style_tags"]:
            counts[tag] = counts.get(tag, 0) + 1

    ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
    return [{"style": style, "count": count} for style, count in ranked[:top_n]]

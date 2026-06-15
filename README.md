# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

---

## How to run

```bash
python app.py        # launches the Gradio UI (open the localhost URL it prints)
python agent.py      # runs the happy path + no-results path in the terminal
python -m pytest tests/ -v   # runs the tool tests
```

---

## Tool Inventory

The agent uses three tools, all in `tools.py`. Each one is a standalone function with a defined input and output.

### Tool 1: `search_listings(description, size, max_price)`

Purpose: Search the mock listings dataset for items matching the user's query, with optional size and price filters.

Inputs:
- `description` (str): keywords describing what the user is looking for (e.g., "vintage graphic tee").
- `size` (str or None): size string to filter by, or None to skip size filtering. Matching is case-insensitive substring (e.g., "M" matches "S/M").
- `max_price` (float or None): maximum price (inclusive), or None to skip price filtering.

Output: a list of matching listing dicts, sorted by relevance (best match first). Each dict has: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand`, `platform`. Returns an empty list `[]` if nothing matches — it never raises.

### Tool 2: `suggest_outfit(new_item, wardrobe)`

Purpose: Given a thrifted item the user is considering and their wardrobe, suggest 1–2 complete outfits using the Groq LLM (`llama-3.3-70b-versatile`).

Inputs:
- `new_item` (dict): the listing dict the user is considering (the top result from `search_listings`).
- `wardrobe` (dict): a wardrobe dict with an `items` key containing a list of wardrobe item dicts.

Output: a non-empty string with 1–2 outfit suggestions that reference real pieces from the wardrobe by name. If the wardrobe is empty, it returns general styling advice for the item instead.

### Tool 3: `create_fit_card(outfit, new_item)`

Purpose: Turn the outfit suggestion and item details into a short, casual, shareable social media caption (Instagram/TikTok style).

Inputs:
- `outfit` (str): the outfit suggestion string returned from `suggest_outfit()`.
- `new_item` (dict): the listing dict for the thrifted item (same one passed to `suggest_outfit`).

Output: a 2–4 sentence caption string that mentions the item name, price, and platform. Uses a higher LLM temperature so the caption is different each time for the same input. If `outfit` is empty or missing, it returns a descriptive error string instead of crashing.

---

## Stretch Features

I added two extra tools (also in `tools.py`). Both run automatically after an item is selected, and their results show up in the listing panel of the UI.

### Tool 4: `compare_price(new_item)`  (Price comparison)

Purpose: Estimate whether the selected item's price is fair by comparing it to similar listings in the dataset (same category that share at least one style tag).

Inputs:
- `new_item` (dict): the listing dict the user is considering (the selected item from `search_listings`).

Output: a dict with `verdict` ("great deal", "fair", "overpriced", or "unknown"), `your_price` (float), `avg_price` (float), `comparable_count` (int), and `message` (str). If there are fewer than 2 comparable listings, it returns `verdict` "unknown" instead of guessing — it never crashes. Example: `$18 is a great deal — similar tops average $22.00 across 14 listings.`

### Tool 5: `get_trending_styles(size)`  (Trend awareness)

Purpose: Surface what styles are popular in the user's size by counting the most common style tags across all listings available in that size.

Inputs:
- `size` (str or None): the size to filter listings by (case-insensitive substring), or None to look across all listings.

Output: a list of `{"style": str, "count": int}` dicts, sorted most popular first. If no listings match the given size, it returns an empty list and the UI just doesn't show a trends line. Example: `vintage (29), classic (16), streetwear (15)`.

---

## Planning Loop

The planning loop lives in `run_agent()` in `agent.py`. It runs the tools one at a time over a single shared `session` dict, and after each tool it checks the session to decide whether to keep going or stop.

1. Initialize the session with `_new_session()` — all result fields start empty and `error` is None.
2. Parse the query with `_parse_query()` to pull out `description`, `size`, and `max_price`. A "$NN" / "under NN" pattern becomes `max_price`; a "size M" or standalone size token becomes `size`; missing ones stay None (the filter is skipped, not failed).
3. Search — call `search_listings(description, size, max_price)`. This is where the loop branches:
   - If the result list is empty→ set `session["error"]` to a specific message and return early, without calling `suggest_outfit`.
   - If it's not empty → set `selected_item = search_results[0]` and continue.
   - (Stretch) After selecting the item, also call `compare_price(selected_item)` → `session["price_check"]` and `get_trending_styles(size)` → `session["trends"]`.
4. Suggest — call `suggest_outfit(selected_item, wardrobe)`. (This tool handles the empty-wardrobe case itself, so the loop doesn't need to branch here.)
5. Fit card — call `create_fit_card(outfit_suggestion, selected_item)`.
6. Return the session. The caller checks `session["error"]` first — if it's None, `session["fit_card"]` holds the result.

The loop is "done" when either `fit_card` is set (success) or `error` is set (early exit). The behavior is adaptive because each tool call depends on what the previous tool wrote into the session — most visibly, an empty search short-circuits the whole run.

---

## State Management

There is one `session` dict (built by `_new_session()` in `agent.py`) that acts as the single source of truth for the whole interaction. The tools never call each other directly and the user never re-enters anything — the loop writes each tool's output into the session, and the next tool reads its input from the session.

What is stored, who writes it, and who reads it:

| Key | Written by | Read by |
|-----|-----------|---------|
| `query` | `_new_session` | parse step |
| `parsed` | parse step | `search_listings` |
| `search_results` | `search_listings` | selection step |
| `selected_item` | selection step | `suggest_outfit`, `create_fit_card` |
| `wardrobe` | `_new_session` | `suggest_outfit` |
| `outfit_suggestion` | `suggest_outfit` | `create_fit_card` |
| `fit_card` | `create_fit_card` | caller / UI |
| `price_check` | `compare_price` (stretch) | caller / UI |
| `trends` | `get_trending_styles` (stretch) | caller / UI |
| `error` | any step | caller / UI |

The flow: `search_listings` writes `search_results` → the loop copies `search_results[0]` into `selected_item` → `suggest_outfit` reads `selected_item` (no re-entry) and writes `outfit_suggestion` → `create_fit_card` reads both `outfit_suggestion` and `selected_item` and writes `fit_card`.

I verified the state actually flows (not re-entered or hardcoded) by checking object identity in testing: `session["selected_item"] is session["search_results"][0]` returned `True`, meaning the exact same dict that came out of search is the one passed into the next two tools. The state lives in memory only for the duration of one `run_agent()` call.

---

## Error Handling

Each tool handles its own failure mode — none of them fail silently or crash the agent.

| Tool | Failure mode | What the agent does |
|------|-------------|---------------------|
| `search_listings` | No listings match the query | The tool returns `[]` (never raises). The planning loop sets `session["error"]` and returns early, without calling `suggest_outfit`. The user sees a specific, actionable message. |
| `suggest_outfit` | Wardrobe is empty (new user) | The tool detects `wardrobe["items"]` is empty and returns general styling advice for the item instead of named outfits. No crash, no empty string — the loop continues normally. |
| `create_fit_card` | Outfit input is empty or missing | The tool guards against an empty/whitespace `outfit` string and returns a descriptive error string instead of crashing. |
| `compare_price` (stretch) | Fewer than 2 comparable listings | The tool returns `verdict` "unknown" with a message instead of guessing or crashing; the rest of the flow continues. |
| `get_trending_styles` (stretch) | No listings match the user's size | The tool returns an empty list and the UI just omits the trends line. |

Concrete example from my testing: I ran the deliberate no-results query `"designer ballgown size XXS under $5"`. Instead of crashing or calling `suggest_outfit` with empty input, the agent returned:

```
error: No listings matched your search (size XXS, under $5). Try broader keywords, raising your max price, or dropping the size filter.
```
and left `selected_item`, `outfit_suggestion`, and `fit_card` all as `None` — proof the loop stopped at the right place. I also confirmed `create_fit_card("", item)` returns `"Unable to generate caption: outfit suggestion was empty or missing."` instead of raising (`tests/test_tools.py::test_create_fit_card_empty_outfit`).

---

## Spec Reflection

One way the spec helped: Writing the Planning Loop and State Management sections of `planning.md` before any code meant I already knew exactly what the `session` dict needed to hold and where the loop should branch. When I implemented `run_agent()`, it was mostly transcribing the steps I'd already written down — the empty-search early return was planned, not bolted on afterward.

One divergence and why: My planning doc didn't mention anything about the LLM temperature for `create_fit_card`. When I tested it, the captions came out almost the same every time. So I raised the temperature in the implementation to get a different caption each run for the same input.

---

## AI Usage

I used Claude as my AI tool. Here are two specific times I used it:

1. Debugging the search (random strings returned results).
I noticed that typing a random string still returned listings. I described the bug to Claude and asked why it happened. It found that `search_listings` was matching keywords as raw substrings with no length filter, so tiny tokens like "a" matched every listing. I had it fix the scorer to drop stopwords and short tokens and match whole words instead of substrings. I checked the fix by re-running junk strings (now return 0, which triggers the no-results message) and real queries (still return matches), then ran my tests.

2. Writing the tests (Milestone 3).
I gave Claude the three failure modes from my Error Handling table and the example tests from the project, and asked it to write pytest tests in `tests/test_tools.py` with at least one test per failure mode. It wrote the tests. I changed them so the tests that call the LLM are skipped when there is no `GROQ_API_KEY` set, so the test run doesn't fail just because a key is missing.

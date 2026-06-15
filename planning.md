# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool will search the mock listings dataset for items matching the description of the user query with optional size and optional price ceiling. It returns the matching items as list. example: [{item1},{item2}..]
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): this is keywords describing what the user is looking for (e.g., "vintage graphic tee").
- `size` (str): Size string to filter by, or None to skip size filtering. Matching is case-insensitive (e.g: "M" matches "S/M")
- `max_price` (float): Maximum price entered by user if any present in the user query(inclusive), or None to skip price filtering. (e.g : "30$")

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
The return contians of the list of item dict that match to the user query,If no matches found then empty list is returned. Each listing dict includes: id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand, platform. Results are sorted by relevance(best matches first)

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If there are no listings match then it should return an empty list. The planning loop then sets an error and stops before suggest_outfit
---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool suggest 1–2 complete outfits using groq (LLM), given a thrifted item the user is considering to buy and the user's wardrobe, 
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The thrifted listing the user considering to buy from the search_listing output.
- `wardrobe` (dict): A wardrobe dict with an 'items' key containing a list of wardrobe item dicts.

**What it returns:**
<!-- Describe the return value -->
A non-empty string with outfit suggestions (1–2 complete looks)
example: Outfit 1: Wear the cream blazer unbuttoned over the white ribbed tank, paired with black trousers and your chunky white sneakers for a clean, polished minimalist vibe with a touch of 90s edge.

Outfit 2: Layer the oversized blazer with the tank tucked in, add the black trousers, and swap to loafers or dress them down with the sneakers if you want a more casual after-hours look.


**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If wardrobe items is empty (new user, no closet yet), the function returns general styling advice, example: "This oversized cream blazer is perfect for layering. Pair it with tailored black pants or jeans for a polished look"
---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Transforms outfit suggestions and item details into a short, casual, shareable social media caption (Instagram/TikTok style) for the thrifted find.


**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion string returned from suggest_outfit().
- 'new_item' (dict):  The listing dict for the thrifted item. (same that was passed to suggest_outfit)

**What it returns:**
<!-- Describe the return value -->
Return 2-4 sentence caption for the social media post, this should include the item name, price and platform. example: "just thrifted this cream oversized blazer on thrift++ for $45 and i'm obsessed, pairs perfectly with basics for that effortless 90s vibe — minimal meets vintage. literally the jacket that makes any outfit instantly cooler"

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If outfit is empty or missing, return a descriptive error message string. example: Unable to generate caption: outfit suggestion was empty or missing.
---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

### Tool 4: compare_price  (Stretch — Price comparison)

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given an item, this tool estimates whether its price is fair by comparing it to similar listings in the dataset (same category and at least one shared style tag). It tells the user if the item is a great deal, fairly priced, or overpriced.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The listing dict the user is considering (the selected item from search_listings).

**What it returns:**
<!-- Describe the return value -->
A dict with the comparison result: `verdict` (str: "great deal", "fair", "overpriced", or "unknown"), `your_price` (float), `avg_price` (float, average of the comparable listings), `comparable_count` (int, how many similar listings were found), and `message` (str, a short human-readable summary). example: {"verdict": "great deal", "your_price": 18.0, "avg_price": 27.5, "comparable_count": 6, "message": "$18 is a great deal — similar tops average $27.50 across 6 listings."}

**What happens if it fails or returns nothing:**
<!-- What should the agent do if there isn't enough data? -->
If there are fewer than 2 comparable listings, there isn't enough data to judge, so it returns `verdict` "unknown" with a message saying so (e.g., "Not enough comparable listings to judge this price."). It never crashes.

### Tool 5: get_trending_styles  (Stretch — Trend awareness)

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Surfaces what styles are currently popular in the user's size by counting the most common style tags across all listings available in that size. This helps the user see what's trending and abundant for them.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `size` (str or None): The size to filter listings by (case-insensitive substring match), or None to look across all listings.

**What it returns:**
<!-- Describe the return value -->
A list of the top style tags with their counts, sorted most popular first. Each entry is a dict with `style` (str) and `count` (int). example: [{"style": "vintage", "count": 12}, {"style": "streetwear", "count": 9}, {"style": "y2k", "count": 7}]

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match the size? -->
If no listings match the given size, it returns an empty list. The agent then tells the user it couldn't find trends for that size instead of showing a blank result.

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

The agent (`run_agent` in `agent.py`) runs the tools one at a time over a single shared `session` dict. After each tool it inspects the session and decides whether to continue or stop — it does not call all three tools unconditionally.

1. Initialize — `session = _new_session(query, wardrobe)`. All result fields start empty and `session["error"] = None`.
2. Parse the query — extract `description`, `size`, and `max_price` from the natural-language query and store them in `session["parsed"]`. A `$NN` / "under NN" pattern → `max_price` (float); a size token (XS/S/M/L/XL) → `size`; the remaining words → `description`. If price or size is absent, that field stays `None` (the filter is skipped, not failed).
3. Search (the adaptive branch) — call `search_listings(description, size, max_price)` and store the list in `session["search_results"]`.
   - If `search_results` is empty→ set `session["error"]` to a specific, actionable message and `return session` immediately. The loop does not call `suggest_outfit` with empty input.
   - If non-empty → set `session["selected_item"] = session["search_results"][0]` (top-ranked result) and continue.
   - (Stretch) After selecting the item, also call `compare_price(selected_item)` → `session["price_check"]` and `get_trending_styles(size)` → `session["trends"]`.
4. Suggest outfit — call `suggest_outfit(selected_item, wardrobe)` and store the result in `session["outfit_suggestion"]`. This tool self-handles the empty-wardrobe case (returns general styling advice), so the loop continues normally.
5. Fit card — call `create_fit_card(outfit_suggestion, selected_item)` and store the result in `session["fit_card"]`.
6. Return — `return session`. The caller checks `session["error"]` first: if it is `None`, `session["fit_card"]` holds the final result; otherwise the run ended early at whichever step set the error.

Done condition: the loop ends when either `session["fit_card"]` is set (success) or `session["error"]` is set (early exit). The behavior is adaptive because each tool call is gated on the state the previous call wrote.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

A single `session` dict (created by `_new_session()` in `agent.py`) is the one source of truth for the whole interaction. Tools never call each other and the user never re-enters anything — the loop writes each tool's output into the session, and the next tool reads its input from the session.

| Key | Written by | Read by | Holds |
|-----|-----------|---------|-------|
| `query` | `_new_session` | parse step | original user text |
| `parsed` | parse step | `search_listings` | `{description, size, max_price}` |
| `search_results` | `search_listings` | selection step | list of matching listing dicts |
| `selected_item` | selection step | `suggest_outfit`, `create_fit_card` | top listing dict (`search_results[0]`) |
| `wardrobe` | `_new_session` | `suggest_outfit` | user's wardrobe dict |
| `outfit_suggestion` | `suggest_outfit` | `create_fit_card` | outfit suggestion string |
| `fit_card` | `create_fit_card` | caller | final caption string |
| `price_check` | `compare_price` (stretch) | caller / UI | price-fairness dict |
| `trends` | `get_trending_styles` (stretch) | caller / UI | list of top style tags |
| `error` | any step | caller | early-exit message, or `None` on success |

**Flow:** `search_listings` writes `search_results` → the loop copies `search_results[0]` into `selected_item` → `suggest_outfit` reads `selected_item` (no re-entry) and writes `outfit_suggestion` → `create_fit_card` reads both `outfit_suggestion` and `selected_item` and writes `fit_card`. The state lives in memory only for the duration of one `run_agent()` call (per-session).

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Tool returns an empty list (never raises). The loop sets `session["error"]` and returns early without calling `suggest_outfit`. User sees a specific, actionable message naming what to change, e.g.: "No listings matched 'vintage graphic tee' under $30. Try raising your max price, dropping the size filter, or using broader keywords." |
| suggest_outfit | Wardrobe is empty (new user, no closet) | Tool does not error — it detects `wardrobe["items"]` is empty and returns general styling advice for the item (what pairs well, what vibe it suits) instead of named outfits. The loop continues normally to `create_fit_card`. |
| create_fit_card | Outfit input is missing or incomplete | Tool guards against an empty/whitespace-only `outfit` string and returns a descriptive error string (not an exception), e.g.: "Unable to generate caption: outfit suggestion was empty or missing." The loop surfaces this to the user rather than producing a blank caption. |
| compare_price (stretch) | Fewer than 2 comparable listings to judge against | Tool returns `verdict` "unknown" with a message ("Not enough comparable listings to judge this price.") instead of guessing or crashing. The rest of the flow continues. |
| get_trending_styles (stretch) | No listings match the user's size | Tool returns an empty list. The UI simply omits the trends line instead of showing a blank result. |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

```
User query + wardrobe
    │
    ▼
Planning Loop (run_agent) ─────────────────────────────────────────────┐
    │                                                                   │
    │  parse query → session["parsed"] = {description, size, max_price} │
    │       │                                                           │
    ├─► search_listings(description, size, max_price)                   │
    │       │ results=[]                                                │
    │       ├──► [ERROR] session["error"]="No listings found..." ──────►│
    │       │                                                           │
    │       │ results=[item, ...]                                       │
    │       ▼                                                           │
    │   Session: search_results=[...]; selected_item = results[0]       │
    │       │                                                           │
    ├─► suggest_outfit(selected_item, wardrobe)                         │
    │       │  (empty wardrobe → general styling advice, no branch)     │
    │       ▼                                                           │
    │   Session: outfit_suggestion = "..."                              │
    │       │                                                           │
    └─► create_fit_card(outfit_suggestion, selected_item)               │
            │                                                           │
        Session: fit_card = "..."                                       │
            │                                                           └─ error path returns here
            ▼
        Return session  (caller checks session["error"] first)

        
```

Data flows through the shared `session` dict: each tool reads its inputs from the session and the loop writes each tool's output back. The error branch is the empty-search case, which sets `session["error"]` and returns before `suggest_outfit` is ever called.

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
I will be using Claude. I'll give it the Tools section of this planning.md (each tool's inputs, return value, and failure mode) one tool at a time, along with the function stubs from `tools.py`, and ask it to write each function — `search_listings` using `load_listings()` from the data loader, and `suggest_outfit` / `create_fit_card` using the Groq LLM. Before using the code I'll check that each tool filters/handles its inputs correctly and returns its failure-mode value instead of crashing (empty list, general advice, error string), then run my pytest tests to confirm.

**Milestone 4 — Planning loop and state management:**
I'll use Claude. I'll give it my Architecture diagram plus the Planning Loop and State Management sections of this planning.md, and ask it to write `run_agent()`. Before using the code I'll check that it stops early when `search_listings` returns an empty list (instead of calling `suggest_outfit`) and that it stores every value in the `session` dict, then verify by printing the session and confirming `selected_item is search_results[0]`.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
At first the agent decides which tool to call first, based on the above query it will be call  the search_listing() tool with input as search_listing(description: vintage graphic tee, size: None, max_price: 30) , this tool returns the list of matching listing , sorted by best matches first. If no matching are found it return an empty list. example output:[
  {
    "id": "l_123",
    "title": "90s Faded Band Tee",
    "description": "Vintage black band t-shirt, boxy fit, faded print",
    "category": "tops",
    "style_tags": ["vintage", "band tee", "grunge"],
    "size": "M",
    "condition": "good",
    "price": 28.0,
    "colors": ["black"],
    "brand": "Unknown",
    "platform": "Depop"
  },
  {
    "id": "l_456",
    "title": "Retro Rock Tee",
    "description": "Soft cotton tee with retro band logo",
    "category": "tops",
    "style_tags": ["vintage", "retro"],
    "size": "S/M",
    "condition": "fair",
    "price": 32.0,
    "colors": ["black", "white"],
    "brand": "Thrifted",
    "platform": "Etsy"
  }
]
the agent picks results[0] → the $28 90s Faded Band Tee
**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
Next the agent decides which tool to call based on the output of the search_listing() tool, the next tool called will be suggest_outfit(). The input for suggest_outfit (new_item: the item the user is considering to buy,listing dict from the pervious output, wardrobe:  wardrobe dict with an 'items' key containing a list of wardrobe item dicts. ), the output of this tool is  A non-empty string with outfit suggestions. If the wardrobe is empty, offer general styling advice for the item rather than raising an exception or returning an empty string. 
Example output (string):
"Outfit 1: Tuck the vintage band tee into the baggy straight-leg jeans, cuff the hem slightly, and finish with chunky white sneakers — a relaxed '90s-inspired streetwear look. Outfit 2: Layer the tee under an oversized denim jacket (or tie the jacket around your waist), add a brown leather belt for shape, and wear combat boots for a grungier vibe.
**Step 3:**
<!-- Continue until the full interaction is complete -->
The next tool called is create_fit_card(outfit: The outfit suggestion string from suggest_outfit(),new_item: The listing dict for the thrifted item.)
Create_fit_card() tool will return a 2–4 sentence string usable as an Instagram/TikTok caption. If outfit is empty or missing, it returns a descriptive error message string. 

**Final output to user:**
<!-- What does the user actually see at the end? -->
The user actually sees the 2-4 sentence string that can be used as caption for the social media post. Example output: thrifted this vintage band tee off depop for $28 and honestly it was made for my wide-legs, full look in my stories.

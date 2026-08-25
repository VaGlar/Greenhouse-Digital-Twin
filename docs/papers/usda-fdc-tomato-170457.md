# USDA FoodData Central — Tomatoes, red, ripe, raw, year round average (FDC ID 170457)

- **Publisher:** USDA FoodData Central
- **URL:** https://fdc.nal.usda.gov/food-details/170457/nutrients
- **Type:** Government nutrient composition database entry
- **Retrieved:** 2026-08-19, via web search (this environment could not open the FDC page directly; figure corroborated via secondary summaries of the same USDA entry)
- **Used for:** `dry_matter_content_fruit` (config/greenhouse_example.yaml)

## Data found

> One cup of red, ripe, raw, year-round average tomatoes weighs 180g, with a water content of 94.5% by weight (vegetable solids content 5.5%).

This corroborates the config's `dry_matter_content_fruit: 0.055` (5.5%). General literature range for ripe tomato dry matter is wider (4–10% depending on variety/growing conditions), but 5.5% is the standard "average" USDA figure and a reasonable default.

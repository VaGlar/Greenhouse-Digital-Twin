# Indeterminate greenhouse tomato cropping cycle duration

- **Type:** Web search aggregation (extension publications, industry guides)
- **Retrieved:** 2026-08-25, via web search
- **Used for:** `simulation.duration_days` (`config/greenhouse_example.yaml`, `twin/params.py`)

## Data used

Found while answering the user's direct question: "is `duration_days: 150` set with some
reasoning, or is it random? What's the plant's actual lifespan?" It was random -- no rationale
existed anywhere in the docs for that number, unlike nearly every other parameter in this project.

> Greenhouse tomato plants may reach a length of 30 to 40 feet in a 10-month season, and indeterminate tomatoes are primarily grown in greenhouses where successively ripening clusters are harvested by hand multiple times over an extended period, in some cases up to a year, to maximize yield.

> Greenhouse tomatoes are indeterminate, which means they produce flowers and fruit throughout the life of the plant. They will continue to grow, flower, and set fruit continuously throughout their entire life until they are ultimately killed by disease, environmental stress, or a decision to terminate them.

Sources (aggregated): [How long do tomato plants live in a greenhouse? — KY Greenhouse](https://www.kygreenhouse.com/industry-news/how-long-do-tomato-plants-live-in-a-greenhouse.html), [Commercial Tomato Production Handbook — UGA CAES Field Report](https://fieldreport.caes.uga.edu/publications/B1312/commercial-tomato-production-handbook/), [Production of Greenhouse Tomatoes — UF/IFAS CV266](https://ask.ifas.ufl.edu/publication/CV266), [Greenhouse Tomato Production — Alabama Cooperative Extension System](https://www.aces.edu/blog/topics/crop-production/greenhouse-tomato-production/).

## Value used

The plant itself has **no natural end-of-life** -- indeterminate growth continues until something
external stops it. Real commercial practice replaces the crop roughly every **10-11 months**
(long enough to justify the labor/heating cost of a new planting, not driven by the plant dying on
its own). Used **330 days (11 months)** as `simulation.duration_days`'s default -- a real-world
crop-cycle-length choice, not a plant biology limit. The model itself has no plant-termination
mechanism either; a longer `duration_days` simply keeps simulating continued growth, which is
consistent with indeterminate biology.

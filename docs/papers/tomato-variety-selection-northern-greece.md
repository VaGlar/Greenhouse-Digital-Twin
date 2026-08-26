# Tomato variety selection for this greenhouse (Northern Greece, CHP + hydroponics)

- **Type:** Web search aggregation (seed company product pages, Greek agricultural press,
  regional greenhouse company profiles)
- **Retrieved:** 2026-08-25/26, via web search
- **Used for:** `crop.variety` (`config/greenhouse_example.yaml`) — descriptive label only so far;
  see "What this does and doesn't change" below.

## Why this needed real research, not a guess

`crop.variety` had been a cosmetic placeholder ("Beefsteak tomato") with no effect on the model
and no sourcing. The user asked to decide it properly, through three lenses: what actually
grows well in Northern Greece, what the market actually wants, and the economics (incl. any
processing/value-add angle) — then asked specifically about a real regional precedent
(Θερμοκήπια Σαββίδη / Dramello Fresh) before settling.

## 1. Regional agronomic fit (Northern Greece / Ημαθία-Πέλλα)

> Η Κεντρική Μακεδονία διαθέτει 5.015 στρέμματα θερμοκηπίων [...] κυρίως σε Ημαθία και Πέλλα.

Confirms this project's weather region (Αλεξάνδρεια Ημαθίας) is a real greenhouse-tomato area,
not an arbitrary choice.

Two named F1 hybrids are explicitly recommended for Northern Greece in Greek seed-supplier
listings:
- **AMATI F1** — semideterminate, 250g+ fruit, suitable for early spring/outdoor planting.
  **Rejected**: semideterminate growth habit conflicts with this project's core assumption of
  a continuous, indeterminate, ~330-day cropping cycle (semideterminate varieties have a more
  limited, finite growth habit, suited to a single seasonal harvest window, not year-round
  high-wire production).
- **BELLADONA F1** — indeterminate, 220-300g fruit, two-stem system, real disease package
  (ToMV, Vd/Va, Fol, C5, TYLCV). **Rejected on a second pass**: explicitly "suitable for spring
  cultivation in Northern Greece [...] not recommended for autumn or winter cultivation" — this
  project's simulation currently starts in September (spans autumn/winter/spring), which is
  exactly the window Belladona isn't suited for in this region. (The user noted the planting
  date itself isn't fixed and could change to fit a variety — but no variety should be picked
  by *first* locking in a planting date that then constrains the search; the variety needs to
  tolerate the actual growing window, not the other way around at this stage.)

Source: Greek seed-supplier listings (geoponiko-parko.gr, sporoprosfores.gr, ProPlant,
Rigakis Seeds) and Greek greenhouse-crop overview (ypaithros.gr, "Ο ελληνικός χάρτης των
θερμοκηπιακών καλλιεργειών").

## 2. Market demand (Greek market)

Three real commercial greenhouse tomato types sold in Greece, per Agrotypos market reporting:

> Ντομάτες τύπου Beef [...] μεγάλου μεγέθους [...] ~1 €/kg. Ντοματίνι τύπου cherry [...] ~3 €/kg
> [...] Ροζ ντομάτα, πιο γευστική [...].

Export trend is shifting toward cherry/specialty (higher value per kg), but a **deeper
beef-vs-cherry comparison** (requested by the user) found gross revenue/m²/year is actually
close between the two (beef: 65-70 kg/m² x ~1€ = ~65-70€/m²; cherry: 20-40 kg/m² x ~3€ =
~60-120€/m²) once real cherry yield figures and labor-cost differences are accounted for —
cherry's harvest is markedly more labor-intensive (weekly picking, delicate handling), eating
into its per-kg price advantage. Net: **beef judged the better overall fit** for this project
(closer net economics once labor is priced in, and it already matches this project's existing
single-stem high-wire density assumption without needing rework) — the user's explicit call
("ας πάμε με beef") after seeing this comparison.

Source: Agrotypos.gr market reporting ("Ζήτηση και ρεκόρ εξαγωγών φέρνουν τιμή 1 ευρώ στις
ντομάτες και 3 ευρώ στα ντοματίνια"); yield/labor figures aggregated from GrowPro/DutchGreenhouses
crop guides and general greenhouse-tomato cost-analysis sources via web search.

## 3. Processing / value-add potential

Greece has a real, substantial tomato processing industry (paste, canned, sauce; ~9 factories,
70% export-oriented) — but it is a **separate supply chain**, built on field-grown processing
cultivars bred for high solids content and mechanical one-time harvest, not greenhouse hydroponic
fresh-market production. **Not a realistic value-add path for this greenhouse** — the only
realistic "processing" outlet would be selling downgraded/Β' διαλογή fruit at a lower price, a
minor secondary revenue stream, not a strategic direction.

Source: Tridge/TomatoNews Greece market overviews (via web search).

## 4. Real regional precedent: Θερμοκήπια Σαββίδη / Dramello Fresh

The user asked specifically to check this real operation before finalizing:

> Θερμοκήπια Σαββίδη [...] Προσοτσάνη, Ν. Δράμας [...] υδροπονική καλλιέργεια με χρήση ΣΗΘΥΑ
> (CHP) [...] 21.000 m² [...] μεγαλόκαρπη τομάτα τύπου beef, 250-280 γραμμαρίων, με την
> επωνυμία "Dramello Fresh".

This is an unusually close real match to this project's own setup: Northern Greece, CHP +
hydroponics, large-scale, beef-type, 250-280g. "Dramello" is the company's own brand name for
its product line, not a disclosed seed cultivar — the underlying variety wasn't found (likely
not publicly disclosed). Source: Clarke Energy (CHP installer case study), Hydroponics.gr,
Dramello.gr, via web search.

Given this real precedent's fruit-weight class (250-280g), two named, Greece-available Rijk
Zwaan hybrids were checked against it:
- **Merlice F1** (De Ruiter/Bayer) — indeterminate, "vigorous... adapted to long production
  cycles from beginning to end", 155-180g, real strong disease package, "suitable for
  year-round greenhouse cultivation", "very good fruit set at high temperatures", grafted onto
  DRO141TX or Maxifort rootstock, available in Greece (rigakisseeds.gr). Closer to a "premium
  cluster/ball" tomato than a full beefsteak size.
- **EYRE RZ F1** (Rijk Zwaan) — 230-280g, matching the Dramello precedent almost exactly. Real
  disease package (ToMV, Fol, For, Pf, Sbl, Va, Vd, intermediate powdery mildew). Marketed for
  "high-tech greenhouse cultivation with high production", "short internodes and balanced
  growth [...] fast flowering and fruit development with uniformity". Available in Greece
  (Rijk Zwaan Hellas). **Indeterminate growth habit was not explicitly confirmed in any source
  found** — inferred with high but not certain confidence, since determinate types are
  essentially never used in this class of high-wire glass/PE greenhouse continuous production.

**Chosen: EYRE RZ F1-class** (230-280g beef tomato) — the closest documented match to a real,
verified Northern Greek CHP+hydroponic operation's actual product, while Merlice remains a
credible fallback if EYRE RZ's growth habit turns out not to fit.

## What this does and doesn't change

This is a **label + documentation update only** (`crop.variety` string, this citation card,
`docs/assumptions/crop-model.md`). No crop-model physics changed yet. The user's own framing:
rather than hard-committing to one exact seed product, identify which crop-model parameters are
*variety-dependent* (target fruit weight, truss rate, fruit-set temperature tolerance, canopy
vigor/LAI parameters) and make those the tunable "dials", sourced to this EYRE RZ F1-class beef
type as the default — so a different real variety later just means different parameter values,
not a rebuilt model. That parameterization is separate, following work (fruit weight/fruit-set
modeling), not part of this step.

**PLACEHOLDER**: a well-researched, real, regionally-plausible choice — not a confirmed seed
order for this specific greenhouse. Replace once/if an actual variety decision is made for the
real installation.

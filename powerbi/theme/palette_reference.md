# Dashboard palette reference (STEP 11)

Dark data-intelligence theme. Surfaces: page `#0B111C`, panel `#141C2B`,
border `#25324A`. Text: primary `#FFFFFF`, body `#E6EDF7`,
muted `#8E9BB3`. Gridlines `#223047`.

## Categorical series (assign in this order, never cycled)

| Order | Hex | Use |
|---|---|---|
| 1 | `#3987E5` | Series 1 |
| 2 | `#D95926` | Series 2 |
| 3 | `#199E70` | Series 3 |
| 4 | `#C98500` | Series 4 |
| 5 | `#D55181` | Series 5 |
| 6 | `#008300` | Series 6 |
| 7 | `#9085E9` | Series 7 |
| 8 | `#E66767` | Series 8 |

The eight hues were checked against the panel surface for lightness band, chroma
floor, colour-vision separation between adjacent pairs, normal-vision separation
and text contrast. The first three pass the all-pairs check, so scatter and
bubble charts use only those three when a legend has three categories.

## Reserved status colours (never used as a data series)

| Meaning | Hex |
|---|---|
| Good | `#0CA30C` |
| Warning | `#FAB219` |
| Serious | `#EC835A` |
| Critical | `#D03B3B` |

## Fixed series meanings on the Prediction & Forecast page

| Series | Hex | Meaning |
|---|---|---|
| Historical | `#3987E5` | Actual delivered revenue |
| Predicted | `#D95926` | Step 8 ML prediction (customer-quarter) |
| Forecast | `#199E70` | Step 9 time-series forecast |

Rules that apply everywhere: one value axis per chart (never a second y-axis), a
legend whenever two or more series are shown, colour never the only cue (labels
and icons carry the same information), and text in a text colour rather than a
series colour.

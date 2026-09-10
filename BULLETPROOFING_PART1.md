# No Place / Part I — Bulletproofing Notes

Every on-slide claim, its source, and where I could and couldn't independently confirm it. You supplied this copy essentially verbatim; this file records what checked out against public reporting and what didn't get checked.

---

## Verified against independent public reporting

| Claim | Slide | Source | Note |
|---|---|---|---|
| Calgary, August 15: caller threatened demolition of Dashmesh Culture Centre by heavy equipment, during services; a second Gurdwara received the same call | 01, 02 | CTV News Calgary, coverage of the threat and the centre's increased security | Independently confirmed |
| Edmonton, August 21: two worshippers stabbed during morning prayers at Nanaksar Gurdwara, shortly after 5 a.m., aged 51 and 75 | 01, 02 | CBC News, CTV News, Global News | Independently confirmed, ages match exactly |
| Suspect released from federal prison the day before the Edmonton attack | 02 | CTV News: "suspect... was released from prison on Thursday" (attack was Friday, August 21) | Independently confirmed |
| Toronto, August 29: man approached a Sikh man at Union Station with slurs and a knife; one hour later, at Queens Quay, stabbed a second victim in the leg | 01, 03 | Toronto Police Service news release, CTV News | Independently confirmed |
| Arrested September 1, charged with six hate-motivated offences | 03 | Toronto Police news release: one count offence-motivated-by-hatred (assault causing bodily harm) plus five counts offence-motivated-by-hatred (assault with a weapon) = six | Independently confirmed, exact count matches |
| Police believe there may be more victims | 03 | Toronto Police news release, directly | Independently confirmed, near-verbatim |
| Winnipeg, September 5: swastikas and threats spray-painted on transit signs along the Nagar Kirtan parade route | 01, 03 | CBC News, CTV News, Winnipeg Police Hate Crimes Unit investigation | Independently confirmed |
| Winnipeg hate crimes rose from 44 to 112 | 03 | CBC News, citing Winnipeg Police Service annual figures | Independently confirmed. The precise figure is a 154% increase, which is more than double. The slide's "more than doubled" is accurate; the plainer "doubled" in your original draft would have slightly understated it, so I kept "more than doubled." |
| 20,000 people attended the Nagar Kirtan parade despite the graffiti | 03 | CBC News, CTV News: organizers expected and reported roughly 20,000 attendees | Independently confirmed |
| Calgary mayor: "There is no place in our city for this hatred or intimidation." | 04 | Public statement circulated in coverage of the Calgary threat | Independently confirmed, exact wording |
| Edmonton mayor: "Hate and prejudice and racism have no place in our city." | 04 | Public statement circulated in coverage of the Edmonton stabbing | Independently confirmed, exact wording |
| Manitoba premier: "Hate and threats have no place in Manitoba." | 04 | Public statement, opening line of a longer post on the Winnipeg graffiti | Independently confirmed, exact wording, matches the lead line of the premier's own statement |

---

## Flagged: attribute by role only, which the slides already do

The Calgary quote traces to a named individual whose title in 2026 I could not independently pin down with full confidence in this session, given how recently Calgary's mayoralty may have changed hands. The slide already attributes it generically as "Mayor of Calgary" rather than by name, which is the right call regardless: it's accurate if that person holds the office, and it keeps the deck consistent with your instruction to avoid naming individuals where a role suffices. If you want a name added, confirm the sitting mayor's identity against a primary source first.

---

## Not independently verified this session

- **The specific word "disgusted" attributed to "the mayor" on slide 05.** The three quotes documented on slide 04 don't contain that word. It may come from a fuller version of one of these officials' remarks that I did not locate, or from a different statement entirely. This is the one line in the deck I could not trace to a specific source. Recommend confirming the exact quote and speaker before posting, or softening the line to reference the documented quotes on slide 04 instead.
- **The precise attribution of the Calgary quote to a specific officeholder**, per above.

---

## Design notes

- Slides 02 and 03 use a new two-incident layout (a dated label, a paragraph, a full-width red divider, then a second dated label and paragraph) built for this installment. It shares the same shell, fonts, accent bar, pips, and footer as Part II, so the two parts sit together as one visual series.
- Slide 04 uses a new pull-quote layout (italic serif quote, small caps red attribution) for the three officials' statements.
- Slides 01, 05, and 06 reuse Part II's exact standard layout function. Fixing this reuse required a small change to `build_carousel.py`: the brand-label text was hardcoded to "NO PLACE / PART II," which would have mislabeled Part I's cover-adjacent slides. It now takes a `brand_text` parameter, defaulting to Part II's original text, so Part II's output is byte-for-byte unaffected. Verified by diff before rendering.
- One rendering bug caught before delivery: the red divider on slide 06 initially failed to render, because slide 06 is built with Part II's `slide_html` function, which didn't carry the `.divider` CSS rule I'd only added to Part I's own template. Fixed by adding that one rule to the shared stylesheet in `build_carousel.py` (confirmed via diff to be the only change, and confirmed by pixel-scanning the re-rendered PNG that the divider now appears).
- All six slides verified by pixel analysis: accent bar full height, six nav pips with the correct one active per slide, footer numbers 01 through 06, dollar sign intact on slide 06, no `#1E1B16` anywhere, series branding present only on slides 01 and 06.

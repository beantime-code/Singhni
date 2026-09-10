# No Place / Part III — Bulletproofing Notes

"The Making of a Machine." Seven slides. This is the highest-risk installment in the series so far, because the topic invites a claim the source material does not support. Read section 0 before posting.

---

## 0. The one thing this deck must not say

**The CRA complaint does not allege money laundering.** It alleges:

1. That 21 charities may fail the **public benefit test** under charity law.
2. That some may be violating the **Income Tax Act** by failing to devote resources to their own charitable activities, supporting **non-qualified donees**, and/or filing inaccurate **T3010** returns.

Those are regulatory and tax-compliance allegations. Money laundering is a criminal offence involving the proceeds of crime. Nothing in the Just Peace Advocates press release, the Sciences Po data, or any reporting I found claims this $46 million is criminal proceeds. As far as anyone alleges, it is lawfully donated money. The question is where it goes, whether it qualifies as charitable, and whether the public should be subsidising it.

So the deck explains the laundering mechanism as **a shape to recognise**, on slide 02, sourced to standard anti-money-laundering training material, and then **explicitly disclaims the accusation** on slide 06. Slide 06 is not a hedge. It is the strongest slide in the deck, because the actual argument is harder to dismiss than an accusation would be: this machine is legal, publicly subsidised, and largely unexamined.

**Never say, in a caption, a comment, a Story, or a reply:**

- that these charities "laundered money"
- that anyone is "under criminal investigation"
- that the money is "dirty," "criminal proceeds," or "illegal"

**Do say:** "a complaint asks the CRA to examine," "the filing alleges," "nothing has been proven."

If someone in the comments says "so you're accusing them of money laundering," the correct answer is: "No. Slide 6 says so directly. Read it again." That exchange is a win, not a problem.

---

## 1. Claim-by-claim sourcing

### Slide 01 — cream, hook

| Claim | Source |
|---|---|
| $46M between organizations in Canada; $21.5M abroad | Just Peace Advocates press release / CRA complaint (as in Part II) |
| "Nobody has ruled any of it illegal" | Accurate as of publication. The CRA has not ruled. |

**Note:** I deliberately did not add $46M and $21.5M into a single "$67.5 million" figure. The press release describes the $21.5M as money sent from those organizations to groups abroad, which may overlap with the $46M moving between them. Adding them risks double-counting. Slide 06 says "tens of millions" for the same reason. Do not let a caption or a reply combine them into one number.

### Slide 02 — dark, the laundering mechanism

| Claim | Source |
|---|---|
| Three stages: placement, layering, integration | Standard AML model, taught universally and documented by compliance training bodies, FATF-aligned |
| Definitions of each stage | Same. The wording is a plain-language paraphrase, not a quotation. |

This slide describes a general mechanism. It makes no claim about any named organization. That separation is deliberate and load-bearing.

### Slide 03 — cream, why Canada

| Claim | Source |
|---|---|
| $45B to $113B laundered in Canada annually | Criminal Intelligence Service Canada estimate, widely cited including in coverage of the Cullen Commission |
| Canada among the easiest places to own a company anonymously | Transparency International Canada, Canadians for Tax Fairness, and evidence heard by the BC money-laundering inquiry |
| Federal beneficial ownership registry in force January 2024 | Canada Business Corporations Act amendments; applies to federally incorporated corporations |
| Transparency International dropped Canada to 12th, citing snow washing | Transparency International Corruption Perceptions Index coverage |

**Caveat worth knowing:** the beneficial ownership registry covers **federally** incorporated corporations. Provincial coverage is uneven. The slide says "a federal beneficial ownership registry," which is precise. Don't let it get paraphrased into "Canada had no registry until 2024," which overstates it.

### Slide 04 — dark, the charity layer

| Claim | Source |
|---|---|
| Registered charities can issue tax receipts, subsidised by foregone public tax | Basic feature of the Income Tax Act |
| Charities may fund "non-qualified donees" | CRA terminology and guidance |
| "Direction and control" replaced in June 2022 by a grant regime | Bill C-19, June 2022; CRA guidance CG-032; new form T1441 alongside the T3010 |
| Canada's risk assessments name charities as the non-profits most exposed to abuse | Canada's 2025 Assessment of Money Laundering and Terrorist Financing Risks; FATF mutual evaluation material |

**Important framing caveat.** The 2022 change is often described by the sector as *reducing* a paternalistic, colonial-era burden on charities working overseas, and it added new reporting requirements rather than removing them. The slide states the change factually and does not call it a loophole. Keep it that way. If challenged, the honest position is: the rule changed, reporting exists, and the open question is how thoroughly anyone audits it.

### Slide 05 — cream, the US and UK block

| Claim | Source |
|---|---|
| 112 RSS-linked organizations in the US, 14 in Canada | Sciences Po CERI "Seeing the Sangh" database, published December 11, 2025, a six-year investigation with The Caravan. Full dataset covers 2,502 organizations across 38 countries. |
| 30 people holding simultaneous positions across the US branch and other Sangh-linked bodies | Reporting on the Savera research into HSS-US |
| Sewa International disbursed more than $17.3M to recipients in India, 2002 to 2012 | Reporting citing that figure, most recipients described as Sangh-affiliated development and relief groups |
| UK Charity Commission statutory inquiry into HSS (UK), opened 2015, reported 2016, found mismanagement | Charity Commission published inquiry report, registered charity number 267309 |
| The same report found no evidence of formal RSS links beyond one speaker's remarks | Same report |

**That last line is deliberate and I recommend keeping it.** It is the single most credibility-protective sentence in the deck. A regulator looked, found administrative mismanagement, and did **not** establish formal RSS links. Including the finding that cuts against the thesis is what makes the rest of the deck hard to attack. Cutting it would be the easiest way to lose an argument in the comments.

### Slide 06 — dark, the turn

Entirely a statement of what is and is not alleged, plus a calibrated question. See section 0. No factual claim beyond the complaint's own contents.

### Slide 07 — dark, CTA

Series recap and sourcing statement. No new claims.

---

## 2. Not verified, or deliberately excluded

- **Any link between the $46M and criminal proceeds.** No source claims this. Excluded entirely.
- **Any claim that the 2022 rule change was made to benefit these organizations,** or that it was lobbied for. No evidence found. Not claimed.
- **US COVID relief figures.** Reporting indicates five US Hindu organizations received roughly $833,000 in SBA pandemic relief. I left this off the slide: it is real but rhetorically weak, since thousands of nonprofits of every description received the same relief, and including it invites an easy rebuttal.
- **The Vishwa Vibhag / "Overseas Department" structure.** Documented in the Savera report and covered by The Wire, and genuinely relevant to a "machine" framing. Left out only for space. It is the strongest candidate for Part IV.

---

## 3. Design and render verification

- Seven slides this installment, not six, to fit the requested dedicated US/UK slide without cutting the explainer. Alternation runs cream, dark, cream, dark, cream, dark, dark. The two dark slides at the end are intentional: slide 06 is the turn and slide 07 is the close, and the design system allows up to two of the same in a row.
- Slide 02 uses a new numbered-step layout. Slide 05 reuses Part I's dual-block layout with a headline added.
- `pips()` and `slide_html()` in `build_carousel.py` previously hardcoded a six-pip total. Both now take a `total` parameter defaulting to 6, so Part III renders seven pips while Parts I and II are byte-for-byte unchanged. Verified by re-rendering both and confirming zero diffs.
- Pixel-verified across all seven: 1080x1350, accent bar full height, seven pips with the correct one active on each slide, footer numbers 01 through 07, all dollar figures intact, no `#1E1B16`.

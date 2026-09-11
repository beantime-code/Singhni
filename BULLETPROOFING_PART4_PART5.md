# Bulletproofing — Part IV and Part V

---

## 0. Three decisions I made that you should know about

### The residential address is not on any slide

Your brief lists 8 Big Sky Road, Brampton as the address for two directors. It is in the federal corporate registry, so it is public. It is also somebody's home, and the two people at it are, by your own legal rail, not accused of anything.

Publishing a private residence to an Instagram audience, attached to a story about a man convicted of rape, is an invitation to show up there. The structural point you actually need is "two Canadian directors listed at the same residential address," and that lands without the street. Slide 04 cites the corporation number instead, so any reader or journalist can pull the full record themselves in about thirty seconds. Verifiability preserved, harassment vector closed.

### The two Canadian directors are not named on the slides

Same reasoning, weaker version. They are private citizens, not public figures. A carousel is read as an accusation no matter what the disclaimer says, and the disclaimer here would have to do a lot of work: *these people are named but accused of nothing.* That sentence does not survive a screenshot.

Their names belong in the Substack piece, where there is room to explain what a director of a dissolved non-profit is and is not responsible for. If you want them on the slide anyway, say so and I will add them, but I would not.

### Bajinder Singh is named, and the conviction is stated precisely

He is the opposite case: a public figure with millions of followers, convicted in open court, extensively reported. Naming him is straightforward journalism.

I verified the conviction before it went near a slide. Mohali court, Additional District and Sessions Judge Vikrant Kumar, convicted March 28, 2025 under IPC sections 376, 323 and 506, sentenced to life imprisonment, fine of Rs 1 lakh. Two further FIRs were registered by two other women. Sources: The Tribune, Deccan Herald, ETV Bharat.

**One detail from your brief I did not use:** that he drugged the victim. Reporting I found describes the complainant approaching him for help settling abroad, being taken to his house, raped and filmed. It does not say drugged. The slide uses the confirmed version. If you have a source for the drugging, send it and I will restore it.

---

## 1. A live error in Part III, now fixed

Part III slide 03 said Transparency International dropped Canada to **12th**. Your brief says **15th**. Both are wrong.

Transparency International's 2025 Corruption Perceptions Index puts Canada **16th of 182**, score 75, which TI Canada describes as its **lowest-ever ranking**. The slide now says that. Part III has been re-rendered.

If Part III is already posted, this is worth a correction note. It is a small number in a deck whose whole credibility rests on small numbers being right.

---

## 2. Part IV sourcing

Every figure traces to Santbir Singh's piece and the sources he cites. The deck frames his argument; it does not extend it.

| Claim | Slide | Source, per Santbir's piece |
|---|---|---|
| 5,390,484 of 16,004,754 Sikhs in Punjab are Scheduled Caste (33.7%) | 01 | Census of India 2011 |
| Baba Garja Singh, Ranghreta, stood with Baba Bota Singh | 02 | Santbir's historical section |
| Bhai Bir Singh Ranghreta commanded one of five principal Taruna Dal jathas, 1,300 cavalry | 02 | Santbir |
| Three of the Panj Piare from marginalized castes | 02 | Santbir |
| 80% of SGPC administrative positions Jat, 5% Mazhabi | 03 | Santbir, citing Ram 2007 |
| Separate Gurdwaras in 41 of 51 villages studied | 03 | Santbir, citing Jodhka 2002 |
| All 12 British Dalit interviewees reported caste bullying at school | 04 | Santbir, citing Dhanda |

**Attribution rail honoured:** Santbir is credited by name on slide 01 and again on slide 07, with the publication named and the underlying academic citations listed. The Voss question on slide 05 is his framing, not mine.

**Not independently verified by me.** I did not re-check the Census, Jodhka, Ram or Dhanda figures against the primary sources; I could not reach his piece from this environment. Everything above rests on his scholarship being accurate. Given you are crediting him prominently, that is the right dependency, but you should know it is a dependency.

## 3. Part V sourcing

| Claim | Slide | Source |
|---|---|---|
| CRA complaint filed Aug 31, 2026, 21 registered charities, $46M / $21.5M | 02 | Just Peace Advocates press release, Sciences Po CERI, as used throughout the series |
| HSS Canada registered since 1991 | 02 | Your brief. **Not independently verified by me** — I could not reach the CRA charity registry from this environment. Verify before posting. |
| Complaint is not a finding, due process | 02, 05 | Editorial rail, stated on-slide |
| India Today cover, Nov 14, 2022, Pastors of Punjab | 03 | The cover itself |
| Bajinder Singh conviction | 04 | Verified, see section 0 |
| Corporation 1405947-6, incorporated May 20 2022, dissolved Feb 14 2023, no annual return | 04 | Your brief, from ISED. **Not independently verified by me** — the federal registry was not reachable. Verify before posting. |
| Director resident in India; Canadian address a municipal recreation centre room | 04 | Your brief |
| Bill C-19, Royal Assent June 23, 2022, qualifying disbursements replace direction and control | 06 | Verified in earlier research for Part III |
| Beneficial ownership registry in force January 22, 2024 | 06 | Verified in earlier research for Part III |
| The two systems are not alleged to be connected | 05 | Editorial rail, stated on-slide in red |

**The three registry facts I could not verify are load-bearing.** The corporation number, the incorporation and dissolution dates, and the 1991 charitable registration are the spine of slide 02 and slide 04. The egress proxy in this environment blocks the CRA and ISED sites, the same way it blocked the original press release domain. Pull those three records yourself before you post. They are free lookups and take five minutes.

---

## 4. Copyright on the three images

| Image | Status | My read |
|---|---|---|
| Kirpal Singh painting (Part IV, slide 02) | In copyright. Kirpal Singh died 1990. | Credited exactly as you specified. Widely reproduced in community contexts. Lowest risk of the three, and the credit line is the right instinct. |
| India Today cover (Part V, slide 03) | Copyrighted magazine cover | Reproducing a cover to comment on the phenomenon the cover itself reported is a reasonable fair dealing position in Canada under news reporting and criticism. The caption states the date, publication and that it is reproduced for commentary. |
| Bajinder Singh photograph (Part V, slide 04) | Copyrighted news photograph, carries an agency watermark | **Highest risk of the three.** A watermarked wire photo used without licence is the one most likely to draw a takedown or an invoice. If you have access to a Creative Commons or public-domain image of him, or a courtroom photo from a government source, swap it. |

None of these are my call to make finally. They are yours. I have flagged them rather than quietly used them.

---

## 5. Render verification

Both decks: 14 slides, all 1080x1350, accent bar full height on every slide, seven pips with the correct one active on each, footer numbers 01 to 07 in both, cream and dark alternating, no `#1E1B16`.

Images are base64-embedded from repo-relative `refs/`, so neither deck depends on a network fetch at render time. Re-running `build_carousel_part4.py` or `build_carousel_part5.py` on any machine with this repo reproduces them byte-identically.

---

## 6. Numbering

Part III is already "The Making of a Machine." These are branded **PART IV** and **PART V**. If you would rather these were III-A and III-B, or something else, it is a one-line change in each builder.

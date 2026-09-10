#!/usr/bin/env python3
"""
No Place / Part I - carousel builder.

Renders six 1080x1350 slides using the Project Aananta design system.
Reuses fonts, colors, and the standard headline+body layout from
build_carousel.py (Part II), and adds three new layouts this part
needs: a dual dated-incident block (slides 02, 03) and a quote block
(slide 04). Slides 01, 05, and 06 reuse the standard layout directly.
"""

import pathlib

from build_carousel import (
    BLACK,
    CREAM,
    FONTS,
    RED,
    TOTAL,
    pips,
    slide_html,
)

HERE = pathlib.Path(__file__).parent
OUT = HERE / "slides_part1"

# Shared CSS additions used by the dual-block and quote layouts. Injected
# into the same shell (bar / wrap / pips / footer) as the standard layout
# in build_carousel.py, so the two parts render pixel-identical frames.
EXTRA_CSS = f"""
.datelabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:29px;
  letter-spacing:1.6px;text-transform:uppercase;color:{RED};margin-bottom:18px;}}
.divider{{display:block;width:100%;height:3px;background:{RED};margin:34px 0;}}
.quoteblock{{margin-bottom:30px;}}
.quotetext{{font-family:'Lora',Georgia,serif;font-style:italic;font-size:32px;
  line-height:1.4;margin-bottom:10px;}}
.quoteattr{{font-family:'Poppins',sans-serif;font-weight:600;font-size:19px;
  letter-spacing:1.6px;text-transform:uppercase;color:{RED};}}
"""


def _shell(num, dark, content_html):
    bg = BLACK if dark else CREAM
    fg = CREAM if dark else BLACK
    rule = "rgba(237,232,223,0.30)" if dark else "rgba(0,0,0,0.25)"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{FONTS}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:1080px;height:1350px;}}
body{{background:{bg};color:{fg};
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeLegibility;}}
.bar{{position:absolute;left:0;top:0;width:18px;height:1350px;background:{RED};}}
.wrap{{position:absolute;left:18px;top:0;width:1062px;height:1350px;
  display:flex;flex-direction:column;padding:74px 78px 210px 62px;}}
.brand{{font-family:'Poppins',sans-serif;font-weight:700;font-size:22px;
  letter-spacing:3px;text-transform:uppercase;color:{RED};margin-bottom:34px;}}
.kicker{{font-family:'Poppins',sans-serif;font-weight:600;font-size:21px;
  letter-spacing:2.6px;text-transform:uppercase;color:{RED};margin-bottom:22px;}}
h1{{font-family:'Poppins',sans-serif;font-weight:700;font-size:74px;
  line-height:1.06;letter-spacing:-1.4px;margin-bottom:40px;}}
.rule{{width:96px;height:5px;background:{RED};margin-bottom:38px;}}
.body{{font-family:'Lora',Georgia,serif;font-size:34px;line-height:1.48;}}
.body p{{margin-bottom:27px;}}
.body p:last-child{{margin-bottom:0;}}
.body b{{font-weight:600;}}
.body .q{{color:{RED};font-weight:600;}}
.body .named{{display:block;margin-bottom:12px;}}
.body .list{{display:block;font-weight:600;line-height:1.34;
  padding-left:26px;border-left:4px solid {RED};}}
.spacer{{flex:1;min-height:24px;}}
{EXTRA_CSS}
.pips{{position:absolute;left:18px;bottom:154px;width:1062px;
  display:flex;justify-content:center;gap:12px;}}
.pip{{width:10px;height:10px;border-radius:50%;display:block;}}
.footer{{position:absolute;left:18px;bottom:0;width:1062px;height:120px;
  border-top:3px solid {rule};
  display:flex;align-items:center;justify-content:space-between;
  padding:0 78px 0 62px;
  font-family:'Poppins',sans-serif;font-weight:700;font-size:22px;
  letter-spacing:2px;text-transform:uppercase;}}
.footer .num{{color:{RED};}}
</style></head><body>
<div class="bar"></div>
<div class="wrap">
  {content_html}
  <div class="spacer"></div>
</div>
{pips(num, dark)}
<div class="footer">
  <span>We need to talk about Canada</span>
  <span class="num">{num:02d}</span>
</div>
</body></html>"""


def dual_slide_html(num, dark, top, bottom):
    """Two dated-incident blocks stacked with a red divider. Slides 02, 03."""

    def block(b):
        paras = "".join(f"<p>{p}</p>" for p in b["body"])
        return f'<div class="datelabel">{b["label"]}</div><div class="body">{paras}</div>'

    content = block(top) + '<span class="divider"></span>' + block(bottom)
    return _shell(num, dark, content)


def quotes_slide_html(num, dark, headline, quotes, closing):
    """A headline, three attributed pull-quotes, and a closing line. Slide 04."""
    qhtml = "".join(
        f'<div class="quoteblock"><p class="quotetext">{text}</p>'
        f'<p class="quoteattr">— {attr}</p></div>'
        for text, attr in quotes
    )
    content = (
        f"<h1>{headline}</h1>"
        f'<div class="rule"></div>'
        f"{qhtml}"
        f'<div class="body"><p>{closing}</p></div>'
    )
    return _shell(num, dark, content)


# ---------------------------------------------------------------------- content
# Every claim below is traceable to public reporting. See
# BULLETPROOFING_PART1.md for per-line sourcing.

def build():
    OUT.mkdir(parents=True, exist_ok=True)

    # Slide 01 — cream, brand, standard layout
    html1 = slide_html(
        1, False, True,
        "Three weeks.<br>Four cities.",
        [
            "<b>Calgary.</b> A Gurdwara told heavy equipment was coming to demolish it.",
            "<b>Edmonton.</b> Two worshippers stabbed during morning prayers.",
            "<b>Toronto.</b> A man with a knife targeted Sikhs at two locations in one night.",
            "<b>Winnipeg.</b> Swastikas on the parade route.",
            '<span class="q">Every time, officials said the same thing.</span>',
        ],
        brand_text="NO PLACE / PART I",
    )

    # Slide 02 — dark, dual dated blocks
    html2 = dual_slide_html(
        2, True,
        top=dict(
            label="Calgary, August 15",
            body=[
                "Dashmesh Culture Centre. A caller told staff heavy equipment was "
                "on the way to demolish the building. People were inside for "
                "services. A second Gurdwara received the same call.",
            ],
        ),
        bottom=dict(
            label="Edmonton, August 21",
            body=[
                "Nanaksar Gurdwara. Shortly after 5&nbsp;a.m. A man entered during "
                "morning prayers and stabbed two worshippers, aged 51 and 75. He "
                "had been released from federal prison the day before.",
            ],
        ),
    )

    # Slide 03 — cream, dual dated blocks
    html3 = dual_slide_html(
        3, False,
        top=dict(
            label="Toronto, August 29",
            body=[
                "Union Station. A man approached a Sikh, made racial slurs, "
                "pulled a knife. One hour later, Queens Quay. Same man, same "
                "slurs. This time he stabbed someone in the leg. He was arrested "
                "September 1 and charged with six hate-motivated offences. "
                "Police believe there may be more victims.",
            ],
        ),
        bottom=dict(
            label="Winnipeg, September 5",
            body=[
                "Swastikas and threats spray-painted on transit signs along the "
                "Nagar Kirtan parade route. Hate crimes in Winnipeg more than "
                "doubled last year, from 44 to 112. The community showed up "
                "anyway. 20,000 people.",
            ],
        ),
    )

    # Slide 04 — dark, quote layout
    html4 = quotes_slide_html(
        4, True,
        "What They Said",
        quotes=[
            (
                "“There is no place in our city for this hatred or intimidation.”",
                "Mayor of Calgary",
            ),
            (
                "“Hate and prejudice and racism have no place in our city.”",
                "Mayor of Edmonton",
            ),
            (
                "“Hate and threats have no place in Manitoba.”",
                "Premier of Manitoba",
            ),
        ],
        closing='Three leaders. Three weeks. The same sentence. '
                '<span class="q">What changed after they said it?</span>',
    )

    # Slide 05 — cream, brand off, standard layout
    html5 = slide_html(
        5, False, False,
        "Ask the Question",
        [
            "“No place” is not a policy. It is a press release.",
            "A man released from federal prison yesterday walked into a "
            "Gurdwara this morning. What system failed between those two doors?",
            "Hate crimes doubled in one city in one year. What changed after "
            "the mayor said the word “disgusted”?",
            'What would have to happen to a Sikh Canadian for the response to '
            'be <span class="q">more than a statement</span>?',
        ],
    )

    # Slide 06 — dark, brand, standard layout with divider + CTA
    html6 = slide_html(
        6, True, True,
        "This is a<br>series now.",
        [
            "Four cities. Three weeks. The same script every time. An "
            "incident, a statement, and nothing structural behind it.",

            "The next installment holds the money. <b>$46 million</b> in "
            "charitable funds. Where it went. Who looked the other way.",

            '<span class="divider"></span>'
            '<span class="q">Full sourced series on Substack. Link in bio.'
            '<br>@projectaananta</span>',
        ],
        brand_text="NO PLACE / PART I",
    )

    for i, html in enumerate([html1, html2, html3, html4, html5, html6], start=1):
        p = OUT / f"slide-{i:02d}.html"
        p.write_text(html, encoding="utf-8")
        print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    build()

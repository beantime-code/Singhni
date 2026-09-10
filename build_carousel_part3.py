#!/usr/bin/env python3
"""
No Place / Part III - "The Making of a Machine" carousel builder.

Seven 1080x1350 slides. Reuses the Project Aananta design system from
build_carousel.py and the dual-block layout from build_carousel_part1.py,
and adds a numbered-steps layout for the money-laundering explainer.

Note on framing: the CRA complaint alleges charity law and Income Tax Act
issues, NOT money laundering. Slides 02-04 explain the general mechanism
and Canada's structural weaknesses, sourced to government and FATF
material. Slide 06 states plainly what is and is not alleged. See
BULLETPROOFING_PART3.md.
"""

import pathlib

from build_carousel import BLACK, CREAM, FONTS, RED, pips, slide_html

HERE = pathlib.Path(__file__).parent
OUT = HERE / "slides_part3"

TOTAL = 7

EXTRA_CSS = f"""
.datelabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:29px;
  letter-spacing:1.6px;text-transform:uppercase;color:{RED};margin-bottom:18px;}}
.divider{{display:block;width:100%;height:3px;background:{RED};margin:30px 0;}}
.step{{display:block;margin-bottom:22px;}}
.stepnum{{font-family:'Poppins',sans-serif;font-weight:700;font-size:22px;
  letter-spacing:2px;color:{RED};display:block;margin-bottom:4px;}}
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
{pips(num, dark, TOTAL)}
<div class="footer">
  <span>We need to talk about Canada</span>
  <span class="num">{num:02d}</span>
</div>
</body></html>"""


def dual_slide_html(num, dark, kicker, headline, top, bottom):
    """Headline plus two labelled blocks split by a red divider."""

    def block(b):
        paras = "".join(f"<p>{p}</p>" for p in b["body"])
        return f'<div class="datelabel">{b["label"]}</div><div class="body">{paras}</div>'

    content = (
        (f'<div class="kicker">{kicker}</div>' if kicker else "")
        + f"<h1>{headline}</h1><div class=\"rule\"></div>"
        + block(top)
        + '<span class="divider"></span>'
        + block(bottom)
    )
    return _shell(num, dark, content)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    D = "$"

    # 01 cream — hook
    s1 = slide_html(
        1, False, True,
        "Nobody builds<br>this by accident.",
        [
            f"<b>{D}46 million</b> moved between organizations inside Canada. "
            f"A further <b>{D}21.5 million</b> left the country. Nobody has "
            "ruled any of it illegal.",

            "That is not a story about one bad charity. It is a structure. "
            "It took decades to build.",

            "Here is how the machine works, in plain language.",

            '<span class="q">Once you see the shape, you cannot unsee it.</span>',
        ],
        brand_text="NO PLACE / PART III", total=TOTAL,
    )

    # 02 dark — the textbook mechanism
    s2 = _shell(2, True,
        '<div class="kicker">The textbook</div>'
        "<h1>Three steps.<br>Every time.</h1>"
        '<div class="rule"></div>'
        '<div class="body">'
        '<p><span class="step"><span class="stepnum">01 &nbsp;PLACEMENT</span>'
        "Get the money into the banking system.</span>"
        '<span class="step"><span class="stepnum">02 &nbsp;LAYERING</span>'
        "Move it between accounts and entities until the trail goes cold.</span>"
        '<span class="step"><span class="stepnum">03 &nbsp;INTEGRATION</span>'
        "Bring it back out looking earned.</span></p>"
        "<p>That is the standard model of money laundering. Every bank "
        "compliance officer on earth is trained on it.</p>"
        '<p><span class="q">Hold that shape in your head.</span></p>'
        "</div>")

    # 03 cream — why Canada
    s3 = slide_html(
        3, False, False,
        "They call it<br>snow washing.",
        [
            "Criminal Intelligence Service Canada estimates that between "
            f"<b>{D}45 billion</b> and <b>{D}113 billion</b> is laundered in this "
            "country every year.",

            "For years Canada was one of the easiest places on earth to own a "
            "company anonymously. A federal beneficial ownership registry only "
            "came into force in January 2024.",

            "Transparency International dropped Canada to 12th on its "
            "corruption index. It named snow washing as a reason.",

            '<span class="q">The word exists because the problem does.</span>',
        ],
        kicker="Why here", total=TOTAL,
    )

    # 04 dark — the charity layer
    s4 = slide_html(
        4, True, False,
        "The part<br>nobody checks.",
        [
            "A registered charity can issue a tax receipt. That means the "
            "public tops up every donation through tax it never collects.",

            "Charities can pass money onward to groups that are not themselves "
            "Canadian charities. The term for those groups is "
            "<b>non-qualified donees</b>.",

            "Until June 2022 a charity had to keep direction and control over "
            "that money. Parliament replaced it with a grant regime, reported "
            "on a form called the T3010.",

            "Canada's own risk assessments name charities as the non-profits "
            "most exposed to abuse.",
        ],
        kicker="The charity layer", total=TOTAL,
    )

    # 05 cream — US and UK, the dedicated slide
    s5 = dual_slide_html(
        5, False,
        "The network",
        "It does not stop<br>at the border.",
        top=dict(
            label="United States",
            body=[
                "Sciences Po's CERI database maps <b>112</b> RSS-linked "
                "organizations in the US, against 14 in Canada. Researchers "
                "found 30 people holding simultaneous positions across the US "
                "branch and other Sangh-linked bodies. One group, Sewa "
                f"International, disbursed more than <b>{D}17.3 million</b> to "
                "recipients in India between 2002 and 2012.",
            ],
        ),
        bottom=dict(
            label="United Kingdom",
            body=[
                "The Charity Commission opened a statutory inquiry into Hindu "
                "Swayamsevak Sangh (UK) in 2015. Its 2016 report found "
                "mismanagement in the charity's administration. It also found "
                "no evidence of formal RSS links beyond one speaker's remarks.",
            ],
        ),
    )

    # 06 dark — the turn, and the guardrail
    s6 = slide_html(
        6, True, False,
        "Nobody has<br>been charged.",
        [
            "The CRA complaint does not allege money laundering. It alleges "
            "something narrower. That 21 charities may fail the public benefit "
            "test, may not be spending on their own charitable activities, and "
            "may have filed inaccurate returns.",

            "No court has ruled. No regulator has found wrongdoing. Every "
            "organization named is entitled to due process.",

            '<span class="q">So ask the harder question. What do you call a '
            "machine that moves tens of millions, collects a public subsidy to "
            "do it, and breaks no law anyone has proven?</span>",
        ],
        kicker="Say it plainly", total=TOTAL,
    )

    # 07 dark — CTA
    s7 = slide_html(
        7, True, True,
        "The Making<br>of a Machine.",
        [
            "Part I was four cities. Part II was the money. Part III is the "
            "structure that carries it.",

            "Every figure here comes from Sciences Po's CERI database, Canadian "
            "government risk assessments, the UK Charity Commission, and the "
            "CRA complaint itself.",

            '<span class="divider"></span>'
            '<span class="q">Full sourced series on Substack. Link in bio.'
            "<br>@projectaananta</span>",
        ],
        brand_text="NO PLACE / PART III", total=TOTAL,
    )

    for i, html in enumerate([s1, s2, s3, s4, s5, s6, s7], start=1):
        p = OUT / f"slide-{i:02d}.html"
        p.write_text(html, encoding="utf-8")
        print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    build()

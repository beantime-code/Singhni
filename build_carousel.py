#!/usr/bin/env python3
"""
No Place / Part II - carousel builder.

Renders six 1080x1350 slides using the Project Aananta design system.
Fonts are embedded as base64 so rendering does not depend on system fonts.
"""

import base64
import os
import pathlib

HERE = pathlib.Path(__file__).parent
FONT_DIR = HERE / "fonts"
OUT = HERE / "slides"

# ---------------------------------------------------------------- design system
CREAM = "#EDE8DF"
BLACK = "#000000"
RED = "#B5261E"

TOTAL = 6


def font_face(family, weight, style, filename):
    data = base64.b64encode((FONT_DIR / filename).read_bytes()).decode()
    return (
        "@font-face{font-family:'%s';font-style:%s;font-weight:%s;"
        "src:url(data:font/woff2;base64,%s) format('woff2');}" % (family, style, weight, data)
    )


FONTS = "".join(
    [
        font_face("Poppins", 400, "normal", "Poppins-400-normal.woff2"),
        font_face("Poppins", 600, "normal", "Poppins-600-normal.woff2"),
        font_face("Poppins", 700, "normal", "Poppins-700-normal.woff2"),
        font_face("Lora", 400, "normal", "Lora-400-normal.woff2"),
        font_face("Lora", 600, "normal", "Lora-600-normal.woff2"),
        font_face("Lora", 400, "italic", "Lora-400-italic.woff2"),
    ]
)


def pips(active, dark):
    inactive = "rgba(237,232,223,0.25)" if dark else "rgba(0,0,0,0.18)"
    dots = "".join(
        '<span class="pip" style="background:%s"></span>'
        % (RED if i == active else inactive)
        for i in range(1, TOTAL + 1)
    )
    return '<div class="pips">%s</div>' % dots


def slide_html(num, dark, brand, headline, body_blocks, kicker=None):
    bg = BLACK if dark else CREAM
    fg = CREAM if dark else BLACK
    rule = "rgba(237,232,223,0.30)" if dark else "rgba(0,0,0,0.25)"

    brand_html = (
        '<div class="brand">NO PLACE / PART II</div>' if brand else ""
    )
    kicker_html = '<div class="kicker">%s</div>' % kicker if kicker else ""
    body_html = "".join("<p>%s</p>" % b for b in body_blocks)

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
  {brand_html}
  {kicker_html}
  <h1>{headline}</h1>
  <div class="rule"></div>
  <div class="body">{body_html}</div>
  <div class="spacer"></div>
</div>
{pips(num, dark)}
<div class="footer">
  <span>We need to talk about Canada</span>
  <span class="num">{num:02d}</span>
</div>
</body></html>"""


# ---------------------------------------------------------------------- content
# Every claim below is traceable. See BULLETPROOFING.md for per-line sourcing.

D = "$"  # written via Python, never through a shell, so the sign cannot be stripped

SLIDES = [
    dict(
        num=1, dark=False, brand=True, kicker=None,
        headline=f"{D}46 million.<br>21 charities.",
        body=[
            "Twenty-one organizations hold registered charity status in Canada. "
            "On August 31, 2026, a complaint filed with the Canada Revenue Agency "
            "asked the agency to examine every one of them.",

            f"The filing traces roughly <b>{D}46 million</b> moving between organizations "
            "it identifies as RSS-affiliated inside Canada.",

            "A charitable tax receipt is a statement by the government. It says this "
            "money serves the public.",

            '<span class="q">Where does charitable money go when nobody checks?</span>',
        ],
    ),
    dict(
        num=2, dark=True, brand=False, kicker="Who they are",
        headline="What the record says",
        body=[
            "The Rashtriya Swayamsevak Sangh was founded in 1925. India has banned it "
            "three times. In 1948. In 1975. In 1992.",

            "In March 2026, the US Commission on International Religious Freedom "
            "recommended targeted sanctions on the RSS, citing responsibility for and "
            "tolerance of severe violations of religious freedom.",

            "In 2018, the CIA World Factbook listed two affiliated organizations, the "
            "Vishva Hindu Parishad and the Bajrang Dal, as religious militant organizations.",

            "These are institutional designations on the public record.",
        ],
    ),
    dict(
        num=3, dark=False, brand=False, kicker="The Canadian pipeline",
        headline="The money has an address",
        body=[
            "The complaint draws on data compiled by the Centre de Recherches "
            "Internationales at Sciences Po.",

            f"It identifies roughly <b>{D}46&nbsp;million</b> moving between RSS-affiliated "
            f"organizations in Canada, and a further <b>{D}21.5&nbsp;million</b> sent from those "
            "organizations to RSS-linked groups abroad.",

            '<span class="named">Four are named at its core:</span>'
            '<span class="list">Hindu Swayamsevak Sangh Canada<br>'
            "Ekal Vidyalaya Foundation of Canada<br>"
            "Vishwa Hindu Parishad of Ontario<br>"
            "Sewa Canada International Aid Inc.</span>",

            '<span class="q">This is a complaint. It is not a finding. The CRA has not ruled.</span>',
        ],
    ),
    dict(
        num=4, dark=True, brand=False, kicker="August 31, 2026",
        headline="He came anyway",
        body=[
            "More than 40 Canadian civil society, human rights, labour and faith "
            "organizations wrote to the Minister of Public Safety. They asked Canada to "
            "deny entry to the RSS chief.",

            "On August 31, 2026, Mohan Bhagwat addressed a gathering in Toronto.",

            "The letters were sent. The entry was granted. Both are on the record.",

            '<span class="q">What is the threshold?</span>',
        ],
    ),
    dict(
        num=5, dark=False, brand=False, kicker="The test",
        headline="What the law<br>already requires",
        body=[
            "Canadian charity law requires that a registered charity deliver a benefit to "
            "the public. Purposes that discriminate on religious grounds cannot be "
            "charitable. Neither can purposes contrary to public policy.",

            "That is the test. It is not new, and it is not in dispute.",

            '<span class="q">What would have to be true for 21 charities to pass that test '
            "while a US federal commission recommends sanctioning the movement the "
            'complaint says they fund?</span>',
        ],
    ),
    dict(
        num=6, dark=True, brand=True, kicker=None,
        headline="This is Part II.",
        body=[
            "Part I covered four cities and three weeks of incidents. Condemnation "
            "without consequence.",

            "Part II is the money. Part III is coming.",

            "Every claim here is traceable to the CRA complaint, the Sciences Po data, or "
            "the USCIRF record. Full sourcing on the Substack.",

            '<span class="q">Link in bio. @projectaananta</span>',
        ],
    ),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for s in SLIDES:
        html = slide_html(
            s["num"], s["dark"], s["brand"], s["headline"], s["body"], s["kicker"]
        )
        p = OUT / f"slide-{s['num']:02d}.html"
        p.write_text(html, encoding="utf-8")
        print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    main()

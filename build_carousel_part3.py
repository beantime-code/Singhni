#!/usr/bin/env python3
"""
No Place / Part III - "The Making of a Machine" carousel builder.

Nine 1080x1350 slides. Reuses the Project Aananta design system from
build_carousel.py and the dual-block layout from build_carousel_part1.py,
and adds three layouts of its own:

  - a numbered-steps layout for the money-laundering explainer (02)
  - a two-track flow layout for the donor journey (05)
  - a horizontal bar layout for the budget comparison (07)

Slides 05 and 07 were previously standalone images built by
build_diagram_hypothetical.py and build_chart_budget.py. They are
rebuilt here from source inside the standard slide shell -- accent bar,
pips, footer, slide number -- rather than pasted in as flat artwork,
and both are cut down for legibility at carousel size. The standalone
builders are kept for the Substack post, where a denser version is
fine because the reader is not swiping.

Note on framing: the CRA complaint alleges charity law and Income Tax
Act issues, NOT money laundering. Slides 02-05 explain the general
mechanism and Canada's structural weaknesses, sourced to government
and FATF material. Slide 05 is an explicitly fictional illustration and
says so twice on its own face. Slide 08 states plainly what is and is
not alleged. See BULLETPROOFING_PART3.md.
"""

import pathlib

from build_carousel import BLACK, CREAM, FONTS, RED, pips, slide_html
from build_diagram_hypothetical import icon_border, icon_check, user_icon

HERE = pathlib.Path(__file__).parent
OUT = HERE / "slides_part3"

TOTAL = 9

EXTRA_CSS = f"""
.datelabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:29px;
  letter-spacing:1.6px;text-transform:uppercase;color:{RED};margin-bottom:18px;}}
.divider{{display:block;width:100%;height:3px;background:{RED};margin:30px 0;}}
.step{{display:block;margin-bottom:22px;}}
.stepnum{{font-family:'Poppins',sans-serif;font-weight:700;font-size:22px;
  letter-spacing:2px;color:{RED};display:block;margin-bottom:4px;}}

/* shared by the two data slides: a shorter headline so the graphic
   gets the room instead */
h1.sm{{font-size:58px;line-height:1.05;margin-bottom:26px;}}
.kickrow{{display:flex;align-items:center;justify-content:space-between;
  gap:20px;margin-bottom:22px;}}
.kickrow .kicker{{margin-bottom:0;}}
.badge{{font-family:'Poppins',sans-serif;font-weight:700;font-size:14px;
  letter-spacing:1.6px;color:{RED};border:1.8px solid {RED};
  border-radius:20px;padding:6px 14px;white-space:nowrap;}}

/* 05 - the donor journey */
.track{{border-radius:6px;padding:24px 24px 26px 24px;margin-bottom:14px;}}
.track.light{{background:rgba(0,0,0,0.05);border:2px solid rgba(0,0,0,0.14);}}
.track.dark{{background:{BLACK};color:{CREAM};}}
.tracklabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:16px;
  letter-spacing:2px;color:{RED};margin-bottom:6px;}}
.trackhead{{font-family:'Poppins',sans-serif;font-weight:700;font-size:31px;
  margin-bottom:18px;}}
.trackrow{{display:flex;align-items:flex-start;justify-content:center;gap:0;}}
.node{{display:flex;flex-direction:column;align-items:center;width:190px;}}
.nodecap{{font-family:'Poppins',sans-serif;font-weight:700;font-size:17px;
  text-align:center;margin-top:8px;line-height:1.28;}}
.nodename{{display:block;min-height:44px;}}
.noderole{{display:block;font-weight:600;font-size:14.5px;opacity:0.66;
  margin-top:2px;}}
.arrow{{display:flex;align-items:flex-start;padding-top:38px;width:30px;
  flex:0 0 30px;opacity:0.85;}}
.bridge{{font-family:'Lora',Georgia,serif;font-style:italic;font-size:22px;
  text-align:center;margin:0 0 14px 0;}}
.foot{{border:2px solid {RED};border-radius:4px;padding:16px 20px;}}
.footlabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:13.5px;
  letter-spacing:2px;color:{RED};margin-bottom:6px;}}
.footbody{{font-family:'Lora',Georgia,serif;font-size:17px;line-height:1.38;}}
.footbody b{{font-weight:600;}}

/* 07 - the budget comparison */
.row{{margin-bottom:46px;}}
.rowlabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:30px;
  margin-bottom:14px;}}
.rowsub{{display:block;font-family:'Poppins',sans-serif;font-weight:600;
  font-size:16px;letter-spacing:0.6px;text-transform:uppercase;
  color:rgba(0,0,0,0.55);margin-top:5px;}}
.barwrap{{position:relative;height:28px;}}
.databar{{position:absolute;left:0;top:0;height:28px;background:{RED};
  border-radius:0 4px 4px 0;}}
.barval{{position:absolute;top:50%;transform:translateY(-50%);
  font-family:'Poppins',sans-serif;font-weight:700;font-size:27px;
  white-space:nowrap;}}
.plain{{background:{BLACK};color:{CREAM};border-radius:4px;
  padding:26px 30px 24px 30px;margin-top:40px;}}
.plainlabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:14px;
  letter-spacing:2px;color:{RED};margin-bottom:12px;}}
.plainline{{font-family:'Lora',Georgia,serif;font-size:23px;line-height:1.38;
  margin-bottom:9px;}}
.plainq{{font-family:'Poppins',sans-serif;font-weight:700;font-size:27px;
  line-height:1.26;color:{RED};margin-top:16px;}}
.plainfoot{{font-family:'Lora',Georgia,serif;font-size:15px;line-height:1.36;
  opacity:0.7;margin-top:14px;padding-top:11px;
  border-top:1px solid rgba(237,232,223,0.25);}}
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


# ------------------------------------------------------------------ 05: the flow

ARROW = (
    f'<div class="arrow"><svg width="30" height="24" viewBox="0 0 34 24">'
    f'<path d="M2 12h26" stroke="{RED}" stroke-width="2.6" fill="none"/>'
    f'<path d="M20 4l10 8-10 8" stroke="{RED}" stroke-width="2.6" fill="none" '
    f'stroke-linecap="round" stroke-linejoin="round"/></svg></div>'
)


def node(icon_html, name, role=None):
    role_html = f'<span class="noderole">{role}</span>' if role else ""
    return (f'<div class="node">{icon_html}<div class="nodecap">'
            f'<span class="nodename">{name}</span>{role_html}</div></div>')


def track(label, head, nodes, dark):
    row = ARROW.join(nodes)
    return (
        f'<div class="track {"dark" if dark else "light"}">'
        f'<div class="tracklabel">{label}</div>'
        f'<div class="trackhead">{head}</div>'
        f'<div class="trackrow">{row}</div></div>'
    )


def flow_slide_html(num):
    """Slide 05. One donation, two endings. Everything on it is invented,
    and it says so in two places: the badge at the top (survives a
    top-cropped screenshot) and the bordered note at the foot."""
    ic = 92
    t1 = track(
        "WHAT SHE THINKS HAPPENS",
        "The money stays at the mandir.",
        [
            node(user_icon("icon-person.png", ic, 72), "She gives", "$500"),
            node(user_icon("icon-temple.png", ic, 72), "Her mandir", "where she prays"),
            node(icon_check(ic), "It stays there", "roof, kitchen, classes"),
        ],
        dark=False,
    )
    t2 = track(
        "WHAT THE LAW ALLOWS INSTEAD",
        "The charity decides, not her.",
        [
            node(user_icon("icon-person.png", ic, 72), "She gives", "$500"),
            node(user_icon("icon-exchange.png", ic, 72),
                 "Sanatan Sanskriti Foundation", "the registered charity"),
            node(user_icon("icon-transfer.png", ic, 72),
                 "Ekta Seva Trust", "granted onward"),
            node(icon_border(ic), "Bharat Vikas Samiti", "abroad"),
        ],
        dark=True,
    )

    content = (
        '<div class="kickrow"><div class="kicker">One donation</div>'
        '<div class="badge">HYPOTHETICAL &middot; INVENTED NAMES</div></div>'
        '<h1 class="sm">Where did it<br>actually go?</h1>'
        '<div class="rule"></div>'
        + t1
        + '<p class="bridge">She gets the same tax receipt either way.</p>'
        + t2
        + '<div class="foot"><div class="footlabel">BEFORE YOU SHARE THIS SLIDE</div>'
        '<p class="footbody">Every name here is invented. None refer to any real '
        "charity or mandir, or to the organizations named in the actual CRA "
        "complaint. This is what Canadian charity law <b>permits</b>, not what "
        "anyone is accused of doing.</p></div>"
    )
    return _shell(num, False, content)


# ----------------------------------------------------------------- 07: the chart

CHART_W = 640
MAX_VAL = 192
BARS = [
    ("CBC/Radio-Canada", "Confirmed &middot; cut this year", 192),
    ("Moved inside Canada", "Alleged &middot; between 21 charities", 46),
    ("Sent out of Canada", "Alleged &middot; left the country", 21.5),
]


def bar_row(label, sub, value):
    w = round(value / MAX_VAL * CHART_W)
    return (
        f'<div class="row"><div class="rowlabel">{label}'
        f'<span class="rowsub">{sub}</span></div>'
        f'<div class="barwrap"><div class="databar" style="width:{w}px;"></div>'
        f'<div class="barval" style="left:{w + 16}px;">${value:g}M</div>'
        f"</div></div>"
    )


def chart_slide_html(num):
    """Slide 07. A bar chart, because this is a magnitude comparison
    across three unrelated categories. Not a pie: these are not parts of
    one whole, and the slide says so."""
    rows = "".join(bar_row(*b) for b in BARS)
    content = (
        '<div class="kicker">Scale</div>'
        '<h1 class="sm">Do the math.</h1>'
        '<div class="rule"></div>'
        + rows
        + '<div class="plain"><div class="plainlabel">IN PLAIN TERMS</div>'
        "<p class=\"plainline\">Ottawa cut $192 million from CBC/Radio-Canada "
        "this year. Canadians argued about it for months.</p>"
        '<p class="plainline">The complaint describes $46 million moving between '
        "charities here, and $21.5 million leaving the country. Nobody was "
        "required to check either one.</p>"
        '<p class="plainq">One of these got a national debate. Which one?</p>'
        '<p class="plainfoot">The two alleged figures are not added together '
        "here: the filing does not say whether one includes the other. These "
        "numbers are not claimed to be connected. The complaint is a complaint, "
        "not a finding, and the CRA has not ruled.</p></div>"
    )
    return _shell(num, False, content)


# ---------------------------------------------------------------------- content


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    D = "$"

    # 01 cream - hook
    s1 = slide_html(
        1, False, True,
        "Nobody builds<br>this by accident.",
        [
            f"<b>{D}46 million</b> moved between organizations inside Canada. "
            f"Another <b>{D}21.5 million</b> left the country.",

            "Nobody has ruled any of it illegal. That is the point.",

            "This is not about one bad charity. It is about a structure, and "
            "it took decades to build.",

            '<span class="q">Here is how it works. In plain language.</span>',
        ],
        brand_text="NO PLACE / PART III", total=TOTAL,
    )

    # 02 dark - the textbook mechanism
    s2 = _shell(2, True,
        '<div class="kicker">Start here</div>'
        "<h1>What laundering<br>actually is.</h1>"
        '<div class="rule"></div>'
        '<div class="body">'
        "<p>Dirty money has one problem. It cannot be spent. Not openly, "
        "not in any amount that matters.</p>"
        '<p><span class="step"><span class="stepnum">01 &nbsp;GET IT IN</span>'
        "Put it somewhere a bank will accept it.</span>"
        '<span class="step"><span class="stepnum">02 &nbsp;MOVE IT</span>'
        "Pass it between accounts and companies until nobody can trace "
        "where it started.</span>"
        '<span class="step"><span class="stepnum">03 &nbsp;TAKE IT OUT</span>'
        "Withdraw it at the far end, looking like ordinary income.</span></p>"
        '<p><span class="q">Three steps. Every country, every time.</span></p>'
        "</div>")

    # 03 cream - why Canada
    s3 = slide_html(
        3, False, False,
        "They call it<br>snow washing.",
        [
            "Canada is an easy place to hide money. That is not an insult. "
            "It is a nickname the industry uses.",

            f"Police estimate between <b>{D}45 billion</b> and <b>{D}113 billion</b> "
            "is laundered here every year.",

            "For years you could own a Canadian company without your name "
            "appearing anywhere. That only changed in January 2024.",

            '<span class="q">Transparency International now ranks Canada 16th '
            "of 182. Its lowest ranking ever.</span>",
        ],
        kicker="Why here", total=TOTAL,
    )

    # 04 dark - the charity layer
    s4 = slide_html(
        4, True, False,
        "The part<br>nobody checks.",
        [
            "A registered charity can hand you a tax receipt. That receipt "
            "means the rest of the country helps pay for your donation, "
            "through tax it never collects.",

            "That charity can then pass the money to a group that is not a "
            "charity at all. Including one in another country.",

            "Until June 2022 it had to stay in control of how that money was "
            "spent. Parliament removed that rule. Now it files a form.",

            '<span class="q">Canada\'s own risk reports name charities as the '
            "most exposed of all non-profits.</span>",
        ],
        kicker="The charity layer", total=TOTAL,
    )

    # 05 cream - the donor journey, folded in from the standalone diagram
    s5 = flow_slide_html(5)

    # 06 dark - US and UK, the dedicated slide
    s6 = dual_slide_html(
        6, True,
        "The network",
        "It does not stop<br>at the border.",
        top=dict(
            label="United States",
            body=[
                "Researchers at Sciences Po mapped <b>112</b> linked "
                "organizations in the United States. Fourteen in Canada. "
                "Thirty people held posts in more than one at the same time. "
                f"One US group sent more than <b>{D}17.3 million</b> to "
                "recipients in India between 2002 and 2012.",
            ],
        ),
        bottom=dict(
            label="United Kingdom",
            body=[
                "Britain's charity regulator investigated the UK branch in "
                "2015. Its 2016 report found mismanagement. It also found no "
                "formal link to the parent organization beyond one speaker's "
                "remarks.",
            ],
        ),
    )

    # 07 cream - the budget comparison, folded in from the standalone chart
    s7 = chart_slide_html(7)

    # 08 dark - the turn, and the guardrail
    s8 = slide_html(
        8, True, False,
        "Nobody has<br>been charged.",
        [
            "Read this slowly. The complaint does not accuse anyone of money "
            "laundering. It says something narrower: that 21 charities may not "
            "be spending on their own charitable work, and may have filed "
            "inaccurate returns.",

            "No court has ruled. No regulator has found wrongdoing. Every "
            "organization named is entitled to due process.",

            '<span class="q">So ask the harder question. What do you call a '
            "machine that moves tens of millions, collects a public subsidy to "
            "do it, and breaks no law anyone has proven?</span>",
        ],
        kicker="Say it plainly", total=TOTAL,
    )

    # 09 dark - CTA
    s9 = slide_html(
        9, True, True,
        "The Making<br>of a Machine.",
        [
            "Part I was four cities. Part II was the money. Part III is the "
            "structure that carries it.",

            "Every figure here comes from Sciences Po's CERI database, Canadian "
            "government risk assessments, the UK Charity Commission, Budget 2026, "
            "and the CRA complaint itself.",

            '<span class="divider"></span>'
            '<span class="q">Full sourced series on Substack. Link in bio.'
            "<br>@projectaananta</span>",
        ],
        brand_text="NO PLACE / PART III", total=TOTAL,
    )

    for i, html in enumerate([s1, s2, s3, s4, s5, s6, s7, s8, s9], start=1):
        p = OUT / f"slide-{i:02d}.html"
        p.write_text(html, encoding="utf-8")
        print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    build()

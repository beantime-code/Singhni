#!/usr/bin/env python3
"""
No Place / Part III - supplementary diagram: "How the Machine Works"

A single 1080x1350 explainer graphic showing the general charity-funding
mechanism mapped onto the three textbook money-laundering stages
(placement, layering, integration). Icons are hand-drawn inline SVG in
a simple open-source line-icon style (Feather/Lucide idiom), so the
file has zero external dependencies and cannot break the way a fetched
icon font or CDN asset could.

This is a standalone asset, not part of the six/seven-slide carousels,
so it carries no page number and no nav pips. It DOES carry the same
disclaimer as Part III slide 06, printed directly into the image,
because infographics get screenshotted and re-shared without their
caption -- the guardrail has to survive that.
"""

import pathlib
from build_carousel import CREAM, BLACK, RED, FONTS

HERE = pathlib.Path(__file__).parent
OUT = HERE / "diagram"


def icon(name, color, size=64):
    """Simple 24x24-viewBox line icons, stroke-based, no external assets."""
    s = f'stroke="{color}" stroke-width="1.7" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    paths = {
        # person: head + shoulders
        "person": f'<circle cx="12" cy="7.5" r="3.4" {s}/><path d="M4.5 20c0-4.2 3.4-6.5 7.5-6.5s7.5 2.3 7.5 6.5" {s}/>',
        # bank / institution: pediment + columns + base
        "bank": f'<path d="M3 9.5 12 4l9 5.5" {s}/><path d="M4.5 9.5v9M8.5 9.5v9M15.5 9.5v9M19.5 9.5v9" {s}/><path d="M3 20.5h18" {s}/><path d="M3 9.5h18" {s}/>',
        # document / grant agreement
        "doc": f'<path d="M6.5 2.8h8l3 3v14.4a.8.8 0 0 1-.8.8H6.5a.8.8 0 0 1-.8-.8V3.6a.8.8 0 0 1 .8-.8Z" {s}/><path d="M14 2.8v3.6h3.2" {s}/><path d="M8.3 12h7.4M8.3 15.2h7.4M8.3 18.4h4.5" {s}/>',
        # right arrow
        "arrow": f'<path d="M3 12h17.5" {s}/><path d="M14.5 5.5 21 12l-6.5 6.5" {s}/>',
        # down arrow
        "arrow-down": f'<path d="M12 3v17.5" {s}/><path d="M5.5 14.5 12 21l6.5-6.5" {s}/>',
        # shuffle / layering: two crossing arrows
        "shuffle": f'<path d="M3 6.5h4.2c2.6 0 3.4 1 4.8 3M3 17.5h4.2c2.6 0 3.4-1 4.8-3" {s}/>'
                   f'<path d="M15 6.5h6M15 17.5h6" {s}/>'
                   f'<path d="M18 3.7 21 6.5l-3 2.8M18 14.7l3 2.8-3 2.8" {s}/>',
        # globe / border crossing
        "globe": f'<circle cx="12" cy="12" r="9" {s}/><path d="M3 12h18" {s}/>'
                 f'<path d="M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18" {s}/>',
        # network / recipient nodes
        "network": f'<circle cx="12" cy="4.5" r="2.3" {s}/><circle cx="5" cy="18.5" r="2.3" {s}/><circle cx="19" cy="18.5" r="2.3" {s}/>'
                   f'<path d="M10.4 6.5 6.6 16.5M13.6 6.5l3.8 10M7.3 18.5h9.4" {s}/>',
        # check circle
        "check": f'<circle cx="12" cy="12" r="9" {s}/><path d="M7.5 12.5 10.3 15.3 16.5 9" {s}/>',
        # receipt / subsidy
        "receipt": f'<path d="M6 2.8h12v18.4l-2.2-1.5-2.2 1.5-2.1-1.5-2.1 1.5-2.2-1.5L6 21.2Z" {s}/>'
                   f'<path d="M8.6 7.5h6.8M8.6 11h6.8M8.6 14.5h4.2" {s}/>',
    }
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
        f'{paths[name]}</svg>'
    )


def stage_band(kicker, headline, row_icons_labels, caption, dark):
    """One horizontal band: red kicker, mini headline, an icon row, a caption."""
    fg = CREAM if dark else BLACK
    ic_color = RED
    row = ""
    for i, (icon_name, label) in enumerate(row_icons_labels):
        if i > 0:
            row += f'<div class="stepicon arrow">{icon("arrow", ic_color, 40)}</div>'
        row += (
            f'<div class="stepicon">{icon(icon_name, ic_color, 64)}'
            f'<div class="steplabel">{label}</div></div>'
        )
    return f"""
    <div class="band {'dark' if dark else 'light'}">
      <div class="bandkicker">{kicker}</div>
      <div class="bandhead">{headline}</div>
      <div class="steprow">{row}</div>
      <p class="bandcaption">{caption}</p>
    </div>
    """


def build():
    OUT.mkdir(parents=True, exist_ok=True)

    band1 = stage_band(
        "STAGE ONE",
        "Placement",
        [("person", "Donor"), ("receipt", "Tax receipt"), ("bank", "Charity")],
        "A donor gives. A registered charity issues a receipt. The public "
        "subsidizes every dollar through tax it never collects.",
        dark=False,
    )
    band2 = stage_band(
        "STAGE TWO",
        "Layering",
        [("bank", "Charity"), ("doc", "Grant"), ("bank", "2nd org")],
        "Money moves charity to charity, or to a non-qualified donee, "
        "under a grant agreement. Each step is a legal transfer, "
        "reported on a form.",
        dark=True,
    )
    band3 = stage_band(
        "STAGE THREE",
        "Integration",
        [("globe", "Border"), ("network", "Recipient")],
        "Funds cross into another country and reach a final recipient, "
        "several steps removed from the original donor.",
        dark=False,
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{FONTS}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:1080px;height:1350px;}}
body{{background:{CREAM};color:{BLACK};
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}}
.bar{{position:absolute;left:0;top:0;width:18px;height:1350px;background:{RED};}}
.wrap{{position:absolute;left:18px;top:0;width:1062px;height:1350px;
  display:flex;flex-direction:column;padding:56px 60px 40px 60px;}}
.brand{{font-family:'Poppins',sans-serif;font-weight:700;font-size:20px;
  letter-spacing:3px;text-transform:uppercase;color:{RED};margin-bottom:18px;}}
h1{{font-family:'Poppins',sans-serif;font-weight:700;font-size:52px;
  line-height:1.05;letter-spacing:-1px;margin-bottom:8px;}}
.subhead{{font-family:'Lora',Georgia,serif;font-style:italic;font-size:22px;
  color:{BLACK};margin-bottom:26px;}}
.band{{border-radius:4px;padding:22px 26px 24px 26px;margin-bottom:14px;}}
.band.light{{background:rgba(0,0,0,0.04);border:2px solid rgba(0,0,0,0.12);}}
.band.dark{{background:{BLACK};color:{CREAM};}}
.bandkicker{{font-family:'Poppins',sans-serif;font-weight:700;font-size:15px;
  letter-spacing:2.4px;color:{RED};margin-bottom:2px;}}
.bandhead{{font-family:'Poppins',sans-serif;font-weight:700;font-size:30px;
  margin-bottom:14px;}}
.steprow{{display:flex;align-items:flex-start;justify-content:center;
  gap:2px;margin-bottom:14px;}}
.stepicon{{display:flex;flex-direction:column;align-items:center;width:110px;}}
.stepicon.arrow{{width:44px;padding-top:14px;opacity:0.85;}}
.steplabel{{font-family:'Poppins',sans-serif;font-weight:600;font-size:15px;
  text-align:center;margin-top:8px;line-height:1.25;}}
.bandcaption{{font-family:'Lora',Georgia,serif;font-size:21px;line-height:1.42;
  text-align:center;max-width:820px;margin:0 auto;}}
.foot{{margin-top:auto;border-top:3px solid rgba(0,0,0,0.25);padding-top:18px;}}
.footlabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:15px;
  letter-spacing:2px;color:{RED};margin-bottom:8px;}}
.footbody{{font-family:'Lora',Georgia,serif;font-size:19px;line-height:1.4;}}
.footbody b{{font-weight:600;}}
</style></head><body>
<div class="bar"></div>
<div class="wrap">
  <div class="brand">NO PLACE / PART III</div>
  <h1>How the machine works.</h1>
  <div class="subhead">Three stages. One legal structure.</div>
  {band1}
  {band2}
  {band3}
  <div class="foot">
    <div class="footlabel">READ THIS BEFORE YOU SHARE THIS IMAGE</div>
    <p class="footbody">
      This diagram shows the <b>general mechanism</b> anti-money-laundering
      training uses. It names no organization. The Canada Revenue Agency
      complaint against 21 charities does <b>not</b> allege money
      laundering. It alleges charity-law and Income Tax Act issues:
      the public benefit test, non-qualified donees, and T3010 accuracy.
      No court has ruled. No regulator has found wrongdoing. Every
      organization named in the series is entitled to due process.
      Full sourcing: Part III, @projectaananta.
    </p>
  </div>
</div>
</body></html>"""

    p = OUT / "diagram.html"
    p.write_text(html, encoding="utf-8")
    print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    build()

#!/usr/bin/env python3
"""
No Place / Part III - supplementary diagram: "How the Machine Works"

v2: fewer, bigger, more distinctive icons. Each stage gets one custom
glyph inside a hand-stamped "case file" ring (a shared visual family:
dashed stamp circle, slight rotation, thicker ink-like stroke) instead
of a repeated row of generic line icons. Boxed band backgrounds are
gone -- stages are separated by a thin red rule and open space, so the
icon carries the personality instead of the chrome.

Zero external assets: every icon is hand-drawn inline SVG, so the file
can't break the way a fetched icon font or the blocked source domain
did earlier in this project.
"""

import pathlib
from build_carousel import CREAM, BLACK, RED, FONTS

HERE = pathlib.Path(__file__).parent
OUT = HERE / "diagram"


def stamp_ring(cx, cy, r=82, dash="6 7", extra=""):
    """The shared 'case file stamp' ring every icon sits inside."""
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{RED}" '
        f'stroke-width="2.4" stroke-dasharray="{dash}" opacity="0.55" {extra}/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r-14}" fill="none" stroke="{RED}" '
        f'stroke-width="1.6" opacity="0.85"/>'
    )


def icon_placement(rot=-4):
    """A stamped coin: a bold $ inside the ring, with a few ink ticks
    around the rim like a rubber stamp caught mid-press."""
    cx, cy = 90, 90
    ticks = "".join(
        f'<line x1="{cx+72*__import__("math").cos(a)}" y1="{cy+72*__import__("math").sin(a)}" '
        f'x2="{cx+84*__import__("math").cos(a)}" y2="{cy+84*__import__("math").sin(a)}" '
        f'stroke="{RED}" stroke-width="2.2" stroke-linecap="round" opacity="0.5"/>'
        for a in [0.35, 1.9, 3.4, 5.0]
    )
    return f"""
    <g transform="rotate({rot} {cx} {cy})">
      {stamp_ring(cx, cy)}
      {ticks}
      <circle cx="{cx}" cy="{cy}" r="34" fill="none" stroke="{RED}" stroke-width="3.4"/>
      <text x="{cx}" y="{cy+15}" font-family="Poppins,sans-serif" font-weight="700"
            font-size="40" fill="{RED}" text-anchor="middle">$</text>
    </g>"""


def icon_layering(rot=3):
    """A hand-off: two overlapping stamp rings with a bold arrow
    passing a packet from one to the other."""
    cx, cy = 90, 90
    return f"""
    <g transform="rotate({rot} {cx} {cy})">
      {stamp_ring(cx-20, cy, r=56, dash="5 6")}
      {stamp_ring(cx+20, cy, r=56, dash="5 6")}
      <path d="M{cx-40} {cy-4} Q{cx} {cy-52} {cx+34} {cy-10}"
            fill="none" stroke="{RED}" stroke-width="4" stroke-linecap="round"/>
      <path d="M{cx+22} {cy-22} L{cx+38} {cy-11} L{cx+21} {cy-3}"
            fill="{RED}"/>
      <rect x="{cx-14}" y="{cy+2}" width="28" height="21" rx="3"
            fill="{CREAM}" stroke="{RED}" stroke-width="3.2"/>
      <line x1="{cx-8}" y1="{cy+12}" x2="{cx+8}" y2="{cy+12}" stroke="{RED}" stroke-width="2.4"/>
    </g>"""


def icon_integration(rot=0):
    """A border crossing: a dashed vertical line, a bold arc leaping
    over it, landing on a single marker pin. No flags, no nation
    symbols, deliberately neutral."""
    cx, cy = 90, 90
    return f"""
    <g transform="rotate({rot} {cx} {cy})">
      {stamp_ring(cx, cy)}
      <line x1="{cx}" y1="{cy-58}" x2="{cx}" y2="{cy+58}"
            stroke="{RED}" stroke-width="2.6" stroke-dasharray="2 8" opacity="0.7"/>
      <path d="M{cx-50} {cy+16} Q{cx} {cy-48} {cx+50} {cy+16}"
            fill="none" stroke="{RED}" stroke-width="4" stroke-linecap="round"/>
      <circle cx="{cx-50}" cy="{cy+16}" r="6" fill="{RED}"/>
      <path d="M{cx+50} {cy+2}
               c-9 0 -16 7 -16 16 c0 11 16 26 16 26 s16 -15 16 -26
               c0 -9 -7 -16 -16 -16 Z"
            fill="{RED}"/>
      <circle cx="{cx+50}" cy="{cy+18}" r="5" fill="{CREAM}"/>
    </g>"""


def stage(kicker, headline, icon_svg, caption, num):
    return f"""
    <div class="stage">
      <div class="stageicon">
        <svg width="200" height="200" viewBox="0 0 180 180" xmlns="http://www.w3.org/2000/svg">{icon_svg}</svg>
      </div>
      <div class="stagetext">
        <div class="stagekicker">STAGE {num} &nbsp;·&nbsp; {kicker}</div>
        <div class="stagehead">{headline}</div>
        <p class="stagecap">{caption}</p>
      </div>
    </div>"""


def build():
    OUT.mkdir(parents=True, exist_ok=True)

    s1 = stage(
        "PLACEMENT", "The public pays in.",
        icon_placement(),
        "A donor gives. A charity issues a receipt. Tax the public never "
        "collects covers part of every dollar.",
        "01",
    )
    s2 = stage(
        "LAYERING", "The handoff.",
        icon_layering(),
        "Money passes charity to charity, or to a non-qualified donee, "
        "under a grant agreement. Each step is legal, on paper.",
        "02",
    )
    s3 = stage(
        "INTEGRATION", "It lands abroad.",
        icon_integration(),
        "Funds cross the border and reach a recipient several steps "
        "removed from the original donor.",
        "03",
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
  display:flex;flex-direction:column;padding:64px 66px 44px 66px;}}
.brand{{font-family:'Poppins',sans-serif;font-weight:700;font-size:20px;
  letter-spacing:3px;text-transform:uppercase;color:{RED};margin-bottom:20px;}}
h1{{font-family:'Poppins',sans-serif;font-weight:700;font-size:56px;
  line-height:1.05;letter-spacing:-1px;margin-bottom:10px;}}
.subhead{{font-family:'Lora',Georgia,serif;font-style:italic;font-size:23px;
  margin-bottom:40px;}}
.stage{{display:flex;align-items:center;gap:40px;padding:46px 0;}}
.stageicon{{flex:0 0 200px;}}
.stagekicker{{font-family:'Poppins',sans-serif;font-weight:700;font-size:16px;
  letter-spacing:2px;color:{RED};margin-bottom:8px;}}
.stagehead{{font-family:'Poppins',sans-serif;font-weight:700;font-size:40px;
  margin-bottom:14px;}}
.stagecap{{font-family:'Lora',Georgia,serif;font-size:24px;line-height:1.45;
  max-width:660px;}}
.rule{{height:2px;background:rgba(0,0,0,0.14);margin:0;}}
.foot{{margin-top:auto;border:2px solid {RED};border-radius:4px;
  padding:20px 24px;}}
.footlabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:14px;
  letter-spacing:2px;color:{RED};margin-bottom:8px;}}
.footbody{{font-family:'Lora',Georgia,serif;font-size:18px;line-height:1.4;}}
.footbody b{{font-weight:600;}}
</style></head><body>
<div class="bar"></div>
<div class="wrap">
  <div class="brand">NO PLACE / PART III</div>
  <h1>How the machine works.</h1>
  <div class="subhead">Three stages. One legal structure.</div>
  {s1}
  <div class="rule"></div>
  {s2}
  <div class="rule"></div>
  {s3}
  <div class="foot">
    <div class="footlabel">READ THIS BEFORE YOU SHARE THIS IMAGE</div>
    <p class="footbody">
      This diagram shows the <b>general mechanism</b>, naming no
      organization. The CRA complaint against 21 charities does
      <b>not</b> allege money laundering. It alleges public-benefit-test
      and Income Tax Act issues. No court has ruled. No regulator has
      found wrongdoing. Every organization named in the series is
      entitled to due process. Full sourcing: Part III, @projectaananta.
    </p>
  </div>
</div>
</body></html>"""

    p = OUT / "diagram.html"
    p.write_text(html, encoding="utf-8")
    print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    build()

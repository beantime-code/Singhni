#!/usr/bin/env python3
"""
No Place / Part III - supplementary diagram: "Where Did It Actually Go?"

A hypothetical donor's journey, told as two tracks: what she believes
happens to her donation, against what the same legal structure can
actually do with it. Fictional organizations throughout, named with
generic Hindi/Sanskrit charitable vocabulary (seva, sanskriti, vikas,
ekta) rather than any variant of the four organizations named in the
real CRA complaint -- close enough to feel like a real Hindu-Canadian
community charity, distant enough that nobody could read it as a claim
about a specific real one. See EXAMPLES_PART3.md for the reasoning.

Four icons are the user's own uploaded reference images (repo-relative
refs/), embedded directly as base64 so there's no network dependency
on img.icons8.com, on a small cream backing plate so the full-color
flat icons stay legible on both the light and dark track. The other
two (the ending check and the border crossing) are this project's own
inline SVG, unchanged. One reference image, a horned skull, is not
used: every open slot in this flow is the overseas recipient
organization, and demon imagery there would assert the group is
monstrous, a claim no source material supports and not something this
project builds.

Carries two disclaimers on purpose: a small persistent badge near the
masthead (survives a top-cropped screenshot) and the full disclaimer
at the bottom the user asked for (survives being read in full).
"""

import base64
import pathlib
from build_carousel import CREAM, BLACK, RED, FONTS

HERE = pathlib.Path(__file__).parent
OUT = HERE / "diagram"
REFS = HERE / "refs"

S = f'stroke="{RED}" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"'


def user_icon(filename, size=100, plate=76):
    """Embed one of the user's own reference PNGs directly (base64,
    no network dependency), on a small cream backing plate so a
    full-color flat icon stays legible on both the light and dark
    track."""
    data = base64.b64encode((REFS / filename).read_bytes()).decode()
    return (
        f'<div style="width:{size}px;height:{size}px;display:flex;'
        f'align-items:center;justify-content:center;">'
        f'<div style="width:{plate}px;height:{plate}px;border-radius:50%;'
        f'background:{CREAM};display:flex;align-items:center;justify-content:center;">'
        f'<img src="data:image/png;base64,{data}" width="{int(plate*0.62)}" '
        f'height="{int(plate*0.62)}" style="display:block;"/></div></div>'
    )


def icon_person(size=100):
    return user_icon("icon-person.png", size)


def icon_temple(size=100):
    return user_icon("icon-temple.png", size)


def icon_exchange(size=100):
    return user_icon("icon-exchange.png", size)


def icon_transfer(size=100):
    return user_icon("icon-transfer.png", size)


def icon_border(size=100):
    """A border crossing: dashed line, an arc leaping it, landing at
    an unmarked point (a plain dot, not a pin -- this destination is
    the unknown one, so it gets no marker, just a question mark)."""
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64">
      <line x1="32" y1="6" x2="32" y2="58" stroke="{RED}" stroke-width="2"
            stroke-dasharray="1 6" opacity="0.65"/>
      <path d="M8 40 Q32 8 56 40" {S}/>
      <circle cx="8" cy="40" r="4" fill="{RED}" stroke="none"/>
      <circle cx="56" cy="40" r="4" fill="{RED}" stroke="none"/>
      <text x="47" y="60" font-family="Poppins,sans-serif" font-weight="700"
            font-size="22" fill="{RED}" text-anchor="middle">?</text>
    </svg>"""


def icon_check(size=88):
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64">
      <circle cx="32" cy="32" r="26" {S}/>
      <path d="M20 33l8 8 16-17" {S}/>
    </svg>"""


def track(label_kicker, label, steps, ending_icon, ending_note, dark):
    fg = CREAM if dark else BLACK
    row = ""
    for i, (icon_svg, cap) in enumerate(steps):
        if i > 0:
            row += (
                f'<div class="arrow"><svg width="34" height="24" viewBox="0 0 34 24">'
                f'<path d="M2 12h26" stroke="{RED}" stroke-width="2.4" fill="none"/>'
                f'<path d="M20 4l10 8-10 8" stroke="{RED}" stroke-width="2.4" '
                f'fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'
            )
        row += f'<div class="step">{icon_svg}<div class="stepcap">{cap}</div></div>'
    row += (
        f'<div class="arrow"><svg width="34" height="24" viewBox="0 0 34 24">'
        f'<path d="M2 12h26" stroke="{RED}" stroke-width="2.4" fill="none"/>'
        f'<path d="M20 4l10 8-10 8" stroke="{RED}" stroke-width="2.4" '
        f'fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'
    )
    row += f'<div class="step end">{ending_icon}<div class="stepcap">{ending_note}</div></div>'
    return f"""
    <div class="track {'dark' if dark else 'light'}">
      <div class="tracklabel">{label_kicker}</div>
      <div class="trackhead">{label}</div>
      <div class="trackrow">{row}</div>
    </div>"""


def build():
    OUT.mkdir(parents=True, exist_ok=True)

    t1 = track(
        "WHAT SHE BELIEVES HAPPENS",
        "She gives at the mandir.",
        [
            (icon_person(), "She gives"),
            (icon_temple(), "The mandir"),
        ],
        icon_check(),
        "Stays there",
        dark=False,
    )

    t2 = track(
        "WHAT THE STRUCTURE ALLOWS",
        "The registered charity decides.",
        [
            (icon_person(), "She gives"),
            (icon_exchange(), "Sanatan Sanskriti Foundation"),
            (icon_transfer(), "Grant to Ekta Seva Trust"),
        ],
        icon_border(),
        "Bharat Vikas Samiti, a name she's never heard",
        dark=True,
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
  display:flex;flex-direction:column;padding:52px 60px 40px 60px;}}
.topline{{display:flex;align-items:center;justify-content:space-between;
  margin-bottom:16px;}}
.brand{{font-family:'Poppins',sans-serif;font-weight:700;font-size:19px;
  letter-spacing:3px;text-transform:uppercase;color:{RED};}}
.badge{{font-family:'Poppins',sans-serif;font-weight:700;font-size:13px;
  letter-spacing:1.5px;color:{RED};border:1.6px solid {RED};border-radius:20px;
  padding:5px 12px;}}
h1{{font-family:'Poppins',sans-serif;font-weight:700;font-size:46px;
  line-height:1.08;letter-spacing:-1px;margin-bottom:8px;}}
.subhead{{font-family:'Lora',Georgia,serif;font-style:italic;font-size:21px;
  margin-bottom:8px;}}
.subnote{{font-family:'Lora',Georgia,serif;font-size:17px;opacity:0.75;
  margin-bottom:26px;}}
.track{{border-radius:6px;padding:38px 30px;margin-bottom:26px;}}
.track.light{{background:rgba(0,0,0,0.045);border:2px solid rgba(0,0,0,0.13);}}
.track.dark{{background:{BLACK};color:{CREAM};}}
.tracklabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:15px;
  letter-spacing:2px;color:{RED};margin-bottom:6px;}}
.trackhead{{font-family:'Poppins',sans-serif;font-weight:700;font-size:32px;
  margin-bottom:28px;}}
.trackrow{{display:flex;align-items:flex-start;justify-content:center;
  flex-wrap:wrap;gap:0;}}
.step{{display:flex;flex-direction:column;align-items:center;width:158px;}}
.step.end{{width:176px;}}
.stepcap{{font-family:'Poppins',sans-serif;font-weight:600;font-size:15.5px;
  text-align:center;margin-top:10px;line-height:1.3;}}
.arrow{{display:flex;align-items:center;padding-top:38px;width:34px;
  flex:0 0 34px;opacity:0.8;}}
.bridge{{font-family:'Lora',Georgia,serif;font-style:italic;font-size:22px;
  text-align:center;margin:6px 0 26px 0;}}
.gap{{flex:1;min-height:20px;}}
.foot{{border:2px solid {RED};border-radius:4px;
  padding:18px 22px;}}
.footlabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:13.5px;
  letter-spacing:2px;color:{RED};margin-bottom:7px;}}
.footbody{{font-family:'Lora',Georgia,serif;font-size:16.5px;line-height:1.4;}}
.footbody b{{font-weight:600;}}
</style></head><body>
<div class="bar"></div>
<div class="wrap">
  <div class="topline">
    <div class="brand">NO PLACE / PART III</div>
    <div class="badge">HYPOTHETICAL &middot; FICTIONAL NAMES</div>
  </div>
  <h1>Where did it actually go?</h1>
  <div class="subhead">One donation. Two possible endings.</div>
  <div class="subnote">A fictional donor, a fictional mandir, fictional organizations.</div>
  {t1}
  <p class="bridge">She never sees the second track. Nothing requires her to.</p>
  {t2}
  <div class="gap"></div>
  <div class="foot">
    <div class="footlabel">READ THIS BEFORE YOU SHARE THIS IMAGE</div>
    <p class="footbody">
      Every name above is invented for this illustration. None refer to
      any real charity, mandir, or the four organizations named in the
      actual CRA complaint. This shows what Canadian charity law
      <b>permits</b> a registered charity to do with donated funds, not
      what any specific organization has done. The real complaint
      alleges charity-law and Income Tax Act issues, <b>not</b> money
      laundering, and the CRA has not ruled. Full sourcing: Part III,
      @projectaananta.
    </p>
  </div>
</div>
</body></html>"""

    p = OUT / "diagram-hypothetical.html"
    p.write_text(html, encoding="utf-8")
    print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    build()

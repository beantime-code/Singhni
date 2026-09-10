#!/usr/bin/env python3
"""
No Place / Part III - supplementary chart: budget comparison.

Renders the three figures from BUDGET_COMPARISON.md as a horizontal
bar chart, per the dataviz skill's guidance: magnitude comparison
across categories is a bar-chart job, not a pie-chart job, and a pie
implies these three numbers are parts of one whole, which they are
not (one is a federal program cut, two are alleged fund movements
from an unrelated complaint). A 3D pie would add perspective
distortion on top of the wrong chart type. See the note in this
project's reply for the full reasoning; this file just builds the
accurate version.

Single series (one hue, red), so no legend -- category labels carry
identity, per the skill's "a single series needs no legend box" rule.
Bars capped at 24px, 4px rounded data-end, square at the baseline,
values labelled at the tip.
"""

import pathlib
from build_carousel import CREAM, BLACK, RED, FONTS

HERE = pathlib.Path(__file__).parent
OUT = HERE / "diagram"

# (label, sublabel, value_in_millions, whether it's the "alleged" category)
BARS = [
    ("CBC/Radio-Canada", "cut this year", 192, False),
    ("Inside Canada", "moved between 21 charities", 46, True),
    ("Sent abroad", "left the country entirely", 21.5, True),
]

CHART_W = 760  # px, at the longest bar (192)
MAX_VAL = 192
BAR_H = 24
ROW_GAP = 90


def bar_row(y, label, sublabel, value, alleged):
    w = round(value / MAX_VAL * CHART_W)
    val_str = f"${value:g}M"
    tag = "ALLEGED" if alleged else "CONFIRMED"
    return f"""
    <div class="row" style="margin-bottom:{ROW_GAP}px;">
      <div class="rowlabel">{label}
        <span class="rowsub">{tag} &middot; {sublabel}</span>
      </div>
      <div class="barwrap">
        <div class="bar" style="width:{w}px;background:{RED};"></div>
        <div class="barval" style="left:{w+14}px;">{val_str}</div>
      </div>
    </div>"""


def build():
    OUT.mkdir(parents=True, exist_ok=True)

    rows = "".join(
        bar_row(0, label, sub, val, alleged) for label, sub, val, alleged in BARS
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{FONTS}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:1080px;height:1350px;}}
body{{background:{CREAM};color:{BLACK};
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}}
.bar_accent{{position:absolute;left:0;top:0;width:18px;height:1350px;background:{RED};}}
.wrap{{position:absolute;left:18px;top:0;width:1062px;height:1350px;
  display:flex;flex-direction:column;}}
.top{{padding:80px 60px 10px 60px;}}
.brand{{font-family:'Poppins',sans-serif;font-weight:700;font-size:19px;
  letter-spacing:3px;text-transform:uppercase;color:{RED};margin-bottom:22px;}}
h1{{font-family:'Poppins',sans-serif;font-weight:700;font-size:66px;
  line-height:1.06;letter-spacing:-1px;margin-bottom:14px;}}
.subhead{{font-family:'Lora',Georgia,serif;font-style:italic;font-size:25px;
  margin-bottom:8px;max-width:920px;}}
.chartarea{{padding:66px 60px 0 60px;}}
.row{{}}
.rowlabel{{font-family:'Poppins',sans-serif;font-weight:700;font-size:26px;
  margin-bottom:18px;}}
.rowsub{{font-family:'Poppins',sans-serif;font-weight:600;font-size:14px;
  letter-spacing:0.5px;color:rgba(0,0,0,0.55);text-transform:uppercase;
  margin-left:10px;}}
.barwrap{{position:relative;height:{BAR_H}px;}}
.bar{{position:absolute;left:0;top:0;height:{BAR_H}px;border-radius:0 4px 4px 0;}}
.barval{{position:absolute;top:50%;transform:translateY(-50%);
  font-family:'Poppins',sans-serif;font-weight:700;font-size:24px;
  color:{BLACK};white-space:nowrap;}}
.axisline{{border-top:1px solid rgba(0,0,0,0.18);margin:2px 0 0 0;
  width:{CHART_W}px;}}
.dark{{margin-top:auto;background:{BLACK};color:{CREAM};
  padding:30px 60px 26px 60px;}}
.vosskicker{{font-family:'Poppins',sans-serif;font-weight:700;font-size:13px;
  letter-spacing:2px;color:{RED};margin-bottom:12px;}}
.vossline{{font-family:'Lora',Georgia,serif;font-size:23px;line-height:1.36;
  margin-bottom:11px;}}
.vossline:last-of-type{{margin-bottom:0;}}
.question{{font-family:'Poppins',sans-serif;font-weight:700;font-size:26px;
  line-height:1.26;color:{RED};margin-top:16px;}}
.foot{{font-family:'Lora',Georgia,serif;font-size:13.5px;line-height:1.35;
  opacity:0.65;margin-top:16px;padding-top:12px;
  border-top:1px solid rgba(237,232,223,0.25);}}
</style></head><body>
<div class="bar_accent"></div>
<div class="wrap">
  <div class="top">
    <div class="brand">NO PLACE / PART III</div>
    <h1>Do the math.</h1>
    <div class="subhead">Three dollar figures. Same country. Same year.</div>
  </div>
  <div class="chartarea">
    {rows}
    <div class="axisline"></div>
  </div>
  <div class="dark">
    <div class="vosskicker">IN PLAIN TERMS</div>
    <p class="vossline">This year, Ottawa cut $192 million from CBC/Radio-Canada.</p>
    <p class="vossline">A complaint says $46 million moved through 21 Canadian charities. Nobody has ruled on it.</p>
    <p class="vossline">The same complaint says $21.5 million left the country. Nobody was required to check.</p>
    <p class="question">An open complaint gets no hearing. A newsroom fund gets cut without a fight. So which one actually gets scrutiny?</p>
    <p class="foot">These figures are not claimed to be connected. The CRA complaint is a complaint, not a finding, and the CRA has not ruled. Full sourcing: BUDGET_COMPARISON.md, Part III, @projectaananta.</p>
  </div>
</div>
</body></html>"""

    p = OUT / "chart-budget.html"
    p.write_text(html, encoding="utf-8")
    print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    build()

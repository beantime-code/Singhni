#!/usr/bin/env python3
"""
Shared image-slide layout for the No Place series.

Adds a photo/artwork slide type to the existing design system: a
full-bleed-width image inside the content column, an italic credit
line beneath it, then body text. Images are base64-embedded from
repo-relative refs/ so the render has no network dependency, the same
way fonts and the donor-journey icons are handled.
"""

import base64
import pathlib

from build_carousel import BLACK, CREAM, FONTS, RED, pips

HERE = pathlib.Path(__file__).parent
REFS = HERE / "refs"


def embed(filename):
    data = base64.b64encode((REFS / filename).read_bytes()).decode()
    return f"data:image/jpeg;base64,{data}"


def image_slide_html(num, dark, headline, image_file, credit, body_blocks,
                     kicker=None, brand_text=None, total=6, img_h=420):
    """A slide carrying one image with a credit line, then body copy."""
    bg = BLACK if dark else CREAM
    fg = CREAM if dark else BLACK
    rule = "rgba(237,232,223,0.30)" if dark else "rgba(0,0,0,0.25)"
    credit_col = "rgba(237,232,223,0.62)" if dark else "rgba(0,0,0,0.58)"

    brand_html = f'<div class="brand">{brand_text}</div>' if brand_text else ""
    kicker_html = f'<div class="kicker">{kicker}</div>' if kicker else ""
    head_html = f"<h1>{headline}</h1>" if headline else ""
    body_html = "".join(f"<p>{b}</p>" for b in body_blocks)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{FONTS}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:1080px;height:1350px;}}
body{{background:{bg};color:{fg};
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}}
.bar{{position:absolute;left:0;top:0;width:18px;height:1350px;background:{RED};}}
.wrap{{position:absolute;left:18px;top:0;width:1062px;height:1350px;
  display:flex;flex-direction:column;padding:64px 78px 200px 62px;}}
.brand{{font-family:'Poppins',sans-serif;font-weight:700;font-size:22px;
  letter-spacing:3px;text-transform:uppercase;color:{RED};margin-bottom:26px;}}
.kicker{{font-family:'Poppins',sans-serif;font-weight:600;font-size:21px;
  letter-spacing:2.6px;text-transform:uppercase;color:{RED};margin-bottom:18px;}}
h1{{font-family:'Poppins',sans-serif;font-weight:700;font-size:62px;
  line-height:1.06;letter-spacing:-1.2px;margin-bottom:26px;}}
.imgbox{{width:100%;height:{img_h}px;overflow:hidden;border-radius:3px;
  margin-bottom:12px;}}
.imgbox img{{width:100%;height:100%;object-fit:cover;object-position:center 22%;
  display:block;}}
.credit{{font-family:'Lora',Georgia,serif;font-style:italic;font-size:17px;
  line-height:1.35;color:{credit_col};margin-bottom:26px;}}
.body{{font-family:'Lora',Georgia,serif;font-size:31px;line-height:1.44;}}
.body p{{margin-bottom:22px;}}
.body p:last-child{{margin-bottom:0;}}
.body b{{font-weight:600;}}
.body .q{{color:{RED};font-weight:600;}}
.spacer{{flex:1;min-height:10px;}}
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
  {brand_html}{kicker_html}{head_html}
  <div class="imgbox"><img src="{embed(image_file)}"/></div>
  <div class="credit">{credit}</div>
  <div class="body">{body_html}</div>
  <div class="spacer"></div>
</div>
{pips(num, dark, total)}
<div class="footer">
  <span>We need to talk about Canada</span>
  <span class="num">{num:02d}</span>
</div>
</body></html>"""

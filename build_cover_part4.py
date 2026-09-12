#!/usr/bin/env python3
"""
No Place / Part IV - cover.

Four historical paintings, arranged as a memorial wall over the series'
black ground with the red accent bar.

Layout reasoning. A four-up grid, every cell the same size. The first
draft gave the one high-resolution file (the sawing, 1024px) a wide
hero band and put the other three in a strip beneath it. That was
wrong twice over: the band crop isolated the blood at the largest
scale on the page, and the hierarchy said one of these four deaths
mattered more than the others. Equal cells fix both. The upscaling
cost is real but small: three sources are 280 to 400px against a 479px
cell, and oil paintings have no fine detail to lose.

Cell order runs cauldron, court, saw, jatha, so the grid ends on the
living rather than the dead, and the sawing sits in the lower row where
the shared bottom gradient is heaviest.

Register. Part III's cover was a Bollywood poster because Part III is
about a machine. Part IV is about a debt, so this one is sober: no
gold, no rays, no billing block gag. Series typography, series colours,
nothing decorative.

The cover names no individual martyr. See BULLETPROOFING_PART4_PART5.md
for why: the sawing and the cauldron are unambiguous depictions of the
November 1675 Delhi martyrdoms, but I cannot identify the third scene or
the elder leading the jatha with enough confidence to print a name on a
cover. Collective attribution is accurate; a wrong name is not.
"""

import base64
import pathlib

from build_carousel import BLACK, CREAM, RED

HERE = pathlib.Path(__file__).parent
OUT = HERE / "cover"
FONT_DIR = HERE / "fonts"
REFS = HERE / "refs"


def font_face(family, weight, filename, style="normal"):
    data = base64.b64encode((FONT_DIR / filename).read_bytes()).decode()
    return (
        f"@font-face{{font-family:'{family}';font-style:{style};"
        f"font-weight:{weight};src:url(data:font/woff2;base64,{data}) "
        f"format('woff2');}}"
    )


FONTS = "".join([
    font_face("Poppins", 700, "Poppins-700-normal.woff2"),
    font_face("Poppins", 600, "Poppins-600-normal.woff2"),
    font_face("Lora", 400, "Lora-400-normal.woff2"),
    font_face("Lora", 400, "Lora-400-italic.woff2", "italic"),
])


def embed(name):
    data = base64.b64encode((REFS / name).read_bytes()).decode()
    return f"data:image/jpeg;base64,{data}"


# The grade. Four paintings of different provenance, resolution and
# colour temperature will read as a scrape unless they are pulled onto
# one tone. Kept gentle: these are devotional images, not stock.
GRADE = "brightness(0.92) contrast(1.02) saturate(0.94) sepia(0.05)"


def build():
    OUT.mkdir(parents=True, exist_ok=True)

    cells = "".join(
        f'<div class="cell"><img src="{embed(f)}" style="object-position:{pos};"/></div>'
        for f, pos in [
            ("img-martyr-cauldron.jpg", "center 45%"),
            ("img-martyr-court.jpg", "center 48%"),
            ("img-martyr-saw.jpg", "center 50%"),
            ("img-jatha-march.jpg", "center 50%"),
        ]
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{FONTS}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:1080px;height:1350px;}}
body{{background:{BLACK};color:{CREAM};overflow:hidden;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}}

.bar{{position:absolute;left:0;top:0;width:18px;height:1350px;
  background:{RED};z-index:9;}}

.wrap{{position:absolute;left:18px;top:0;width:1062px;height:1350px;
  display:flex;flex-direction:column;align-items:center;
  padding:52px 56px 0 40px;}}

.brandrow{{display:flex;align-items:center;gap:16px;margin-bottom:26px;}}
.brandrow .dash{{width:56px;height:3px;background:{RED};}}
.brand{{font-family:'Poppins',sans-serif;font-weight:700;font-size:21px;
  letter-spacing:5px;text-transform:uppercase;color:{RED};}}

.grid{{display:grid;grid-template-columns:479px 479px;gap:8px;}}
.cell{{width:479px;height:344px;overflow:hidden;position:relative;}}
.cell img{{width:100%;height:100%;object-fit:cover;display:block;
  filter:{GRADE};}}

/* one shared shadow across every frame, so the four read as one object
   and the block settles into the ground instead of floating on it */
.cell::after{{content:'';position:absolute;inset:0;
  background:linear-gradient(180deg, rgba(0,0,0,0.08) 0%,
    rgba(0,0,0,0) 36%, rgba(0,0,0,0.30) 100%);}}

.title{{font-family:'Poppins',sans-serif;font-weight:700;font-size:78px;
  line-height:1.05;letter-spacing:-1.6px;text-align:center;margin-top:44px;}}
.rule{{width:120px;height:5px;background:{RED};margin:24px 0;}}
.strap{{font-family:'Lora',Georgia,serif;font-style:italic;font-size:27px;
  line-height:1.42;text-align:center;max-width:800px;
  color:rgba(237,232,223,0.92);}}

.foot{{position:absolute;left:18px;bottom:0;width:1062px;
  padding:0 56px 40px 40px;text-align:center;}}
.credit{{font-family:'Lora',Georgia,serif;font-size:16px;line-height:1.4;
  color:rgba(237,232,223,0.55);max-width:820px;margin:0 auto 16px auto;}}
.billing{{font-family:'Poppins',sans-serif;font-weight:600;font-size:14px;
  letter-spacing:3px;text-transform:uppercase;color:{RED};
  padding-top:16px;border-top:1px solid rgba(237,232,223,0.18);}}
</style></head><body>
<div class="bar"></div>

<div class="wrap">
  <div class="brandrow">
    <span class="dash"></span>
    <span class="brand">No Place &nbsp;/&nbsp; Part IV</span>
    <span class="dash"></span>
  </div>

  <div class="grid">{cells}</div>

  <div class="title">The Door<br>We Left Open</div>
  <div class="rule"></div>
  <div class="strap">They paid for this Panth with their lives.<br>
  One in three Sikhs in Punjab was never handed the whole of it.</div>
</div>

<div class="foot">
  <div class="credit">Traditional depictions of Sikh martyrdom and of the
  Khalsa in arms. Artists unattributed.</div>
  <div class="billing">The argument belongs to Santbir Singh
  &nbsp;&middot;&nbsp; @projectaananta</div>
</div>
</body></html>"""

    p = OUT / "cover-part4.html"
    p.write_text(html, encoding="utf-8")
    print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    build()

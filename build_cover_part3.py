#!/usr/bin/env python3
"""
No Place / Part III - cover, built as a Bollywood film poster.

Deliberate stylistic departure from the series' cream/black/red system:
this is a poster, not a slide. Gold gradient title, heavy outline,
radiating light behind the art, a billing block at the foot. The
series wordmark and the red accent bar keep it tied to the rest.

Title runs in three scripts: Gurmukhi, Devanagari, English.
  ਮਨੀ ਲਾਂਡਰਿੰਗ  /  मनी लॉन्ड्रिंग  /  MONEY LAUNDERING

The Punjabi tagline is the actual idiom for the thing, "making black
money white," rather than a translation of an English slogan.

The billing block bills the three stages of laundering as the cast.
It bills no organization, because Part III's whole guardrail is that
the CRA complaint does not allege money laundering against anyone.
"""

import base64
import pathlib

from build_carousel import RED

HERE = pathlib.Path(__file__).parent
OUT = HERE / "cover"
FONT_DIR = HERE / "fonts"
REFS = HERE / "refs"

GOLD_HI = "#FFE9A8"
GOLD_MID = "#F2C14E"
GOLD_LO = "#B87914"
INK = "#0B1620"


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
    font_face("Lora", 400, "Lora-400-normal.woff2", "normal"),
    font_face("Lora", 400, "Lora-400-italic.woff2", "italic"),
    font_face("NotoDeva", "100 900", "NotoDevanagari.woff2"),
    font_face("NotoGuru", "100 900", "NotoGurmukhi.woff2"),
])


def embed(name):
    data = base64.b64encode((REFS / name).read_bytes()).decode()
    return f"data:image/jpeg;base64,{data}"


def build():
    OUT.mkdir(parents=True, exist_ok=True)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{FONTS}
*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:1080px;height:1350px;}}
body{{background:{INK};overflow:hidden;}}

/* radiating light behind everything, the poster starburst */
.rays{{position:absolute;left:50%;top:300px;width:2000px;height:2000px;
  transform:translateX(-50%);
  background:repeating-conic-gradient(from 0deg at 50% 50%,
    rgba(255,225,150,0.10) 0deg 7deg, rgba(255,225,150,0) 7deg 16deg);}}
.glow{{position:absolute;left:50%;top:250px;width:1500px;height:1200px;
  transform:translateX(-50%);
  background:radial-gradient(ellipse at center,
    rgba(90,150,180,0.55) 0%, rgba(11,22,32,0) 62%);}}
.vignette{{position:absolute;inset:0;
  background:radial-gradient(ellipse at 50% 42%,
    rgba(0,0,0,0) 38%, rgba(0,0,0,0.72) 100%);}}

.bar{{position:absolute;left:0;top:0;width:18px;height:1350px;background:{RED};
  z-index:9;}}

.wrap{{position:absolute;inset:0;z-index:5;
  display:flex;flex-direction:column;align-items:center;
  padding:44px 58px 0 62px;}}

.brandrow{{display:flex;align-items:center;gap:14px;margin-bottom:14px;}}
.brandrow .dash{{width:52px;height:3px;background:{RED};}}
.brand{{font-family:'Poppins',sans-serif;font-weight:700;font-size:21px;
  letter-spacing:5px;color:{GOLD_MID};text-transform:uppercase;}}

.art{{width:856px;height:516px;margin-top:6px;overflow:hidden;
  border-radius:4px;
  -webkit-mask-image:radial-gradient(ellipse at 50% 46%,
    #000 52%, rgba(0,0,0,0.25) 84%, rgba(0,0,0,0) 100%);}}
.art img{{width:100%;height:100%;object-fit:cover;object-position:center 46%;
  display:block;}}

.tagline{{font-family:'NotoGuru','Poppins',sans-serif;font-weight:600;
  font-size:30px;color:{GOLD_HI};letter-spacing:0.5px;
  margin-top:2px;text-shadow:0 2px 10px rgba(0,0,0,0.85);}}

.titlewrap{{text-align:center;margin-top:14px;}}
.t-guru{{font-family:'NotoGuru',sans-serif;font-weight:900;font-size:112px;
  line-height:1.16;
  background:linear-gradient(180deg,{GOLD_HI} 4%,{GOLD_MID} 46%,{GOLD_LO} 99%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  -webkit-text-stroke:3px rgba(0,0,0,0.55);
  filter:drop-shadow(0 5px 0 rgba(0,0,0,0.6)) drop-shadow(0 16px 26px rgba(0,0,0,0.75));}}
.t-deva{{font-family:'NotoDeva',sans-serif;font-weight:900;font-size:74px;
  line-height:1.3;margin-top:-2px;
  background:linear-gradient(180deg,{GOLD_HI} 8%,{GOLD_MID} 55%,{GOLD_LO} 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  -webkit-text-stroke:2.4px rgba(0,0,0,0.5);
  filter:drop-shadow(0 4px 0 rgba(0,0,0,0.55)) drop-shadow(0 12px 20px rgba(0,0,0,0.7));}}
.t-en{{font-family:'Poppins',sans-serif;font-weight:700;font-size:38px;
  letter-spacing:11px;color:#F4EFE4;margin-top:12px;
  text-shadow:0 3px 14px rgba(0,0,0,0.9);}}

.strap{{margin-top:30px;font-family:'Lora',Georgia,serif;font-style:italic;
  font-size:26px;color:rgba(244,239,228,0.92);text-align:center;
  max-width:830px;line-height:1.34;
  text-shadow:0 2px 12px rgba(0,0,0,0.9);}}

.billing{{position:absolute;left:18px;bottom:0;width:1062px;
  padding:20px 60px 24px 44px;text-align:center;
  background:linear-gradient(180deg, rgba(11,22,32,0) 0%, rgba(11,22,32,0.9) 34%);}}
.bill1{{font-family:'Poppins',sans-serif;font-weight:600;font-size:16px;
  letter-spacing:3.4px;color:{GOLD_MID};text-transform:uppercase;
  line-height:1.85;}}
.bill2{{font-family:'Poppins',sans-serif;font-weight:600;font-size:13.5px;
  letter-spacing:2.6px;color:rgba(244,239,228,0.62);text-transform:uppercase;
  margin-top:9px;line-height:1.8;}}
.rule{{width:150px;height:2px;background:rgba(242,193,78,0.55);
  margin:14px auto 12px auto;}}
</style></head><body>
<div class="rays"></div>
<div class="glow"></div>
<div class="vignette"></div>
<div class="bar"></div>

<div class="wrap">
  <div class="brandrow">
    <span class="dash"></span>
    <span class="brand">No Place &nbsp;/&nbsp; Part III</span>
    <span class="dash"></span>
  </div>

  <div class="art"><img src="{embed('img-laundering-iso.jpg')}"/></div>

  <div class="tagline">ਕਾਲੇ ਧਨ ਨੂੰ ਸਫ਼ੈਦ ਬਣਾਉਣਾ</div>

  <div class="titlewrap">
    <div class="t-guru">ਮਨੀ ਲਾਂਡਰਿੰਗ</div>
    <div class="t-deva">मनी लॉन्ड्रिंग</div>
    <div class="t-en">MONEY LAUNDERING</div>
  </div>

  <div class="strap">Three steps. One legal structure.<br>
  And a country that never checks the receipts.</div>
</div>

<div class="billing">
  <div class="rule"></div>
  <div class="bill1">Starring &nbsp;&middot;&nbsp; Placement &nbsp;&middot;&nbsp;
    Layering &nbsp;&middot;&nbsp; Integration</div>
  <div class="bill2">A Canadian Story &nbsp;&middot;&nbsp; Swipe To Understand It
    &nbsp;&middot;&nbsp; @projectaananta</div>
</div>
</body></html>"""

    p = OUT / "cover-part3.html"
    p.write_text(html, encoding="utf-8")
    print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    build()

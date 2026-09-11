#!/usr/bin/env python3
"""
No Place / Part V - "The Systems That Walked Through It"

Carousel B from the master assembly brief: the two structures that
filled the vacuum Part IV describes. The charity channel (CRA) and the
non-profit channel (ISED).

Editorial rails enforced here, not optional:
  - The CRA complaint is a complaint, not a finding. Said on the slide.
  - The two systems are NOT alleged to be connected. Said on the slide.
  - No allegation against the Canadian directors of the dissolved
    non-profit. They are not named, and their residential address is
    not published. The corporation number is cited instead so the
    record stays verifiable without doxxing private individuals.
  - Bajinder Singh is named: public figure, convicted, extensively
    reported. The conviction is stated with court, date and sentence.

India-blocking hardening: the highest-trigger material from Part II
(the Golwalkar quote, the Nazi-Germany line, Bhagwat) is deliberately
absent here. Organization names appear once, where sourcing requires
them, and are referred to structurally after that.
"""

import pathlib

from build_carousel import slide_html
from layout_image import image_slide_html

HERE = pathlib.Path(__file__).parent
OUT = HERE / "slides_part5"
TOTAL = 7
BRAND = "NO PLACE / PART V"
D = "$"


def build():
    OUT.mkdir(parents=True, exist_ok=True)

    # 01 cream - hook
    s1 = slide_html(
        1, False, True,
        "Two systems.<br>One target.",
        [
            "Part IV described a vacancy. This is what moved into it.",

            "One operates in daylight with charitable tax receipts and decades "
            "of institutional cover. One operated in the dark for eight months "
            "and dissolved itself.",

            "Both used Canadian legal structures. Both served operations "
            "abroad. Both drew from the same community.",

            '<span class="q">Neither was stopped by the regulator responsible '
            "for it.</span>",
        ],
        brand_text=BRAND, total=TOTAL,
    )

    # 02 dark - the charity channel
    s2 = slide_html(
        2, True, False,
        "The daylight<br>channel.",
        [
            "A complaint filed with the Canada Revenue Agency on August 31, "
            "2026 asks it to examine 21 registered charities. Using Sciences "
            "Po CERI data, it traces roughly <b>{d}46 million</b> moving between "
            "affiliated organizations in Canada and <b>{d}21.5 million</b> sent "
            "abroad.".format(d=D),

            "Hindu Swayamsevak Sangh Canada has held charitable registration "
            "since 1991. Thirty-four years of tax receipts.",

            '<span class="q">This is a complaint. It is not a finding. The CRA '
            "has not ruled, and every organization named is entitled to due "
            "process.</span>",
        ],
        kicker="System one", total=TOTAL,
    )

    # 03 cream - the wave, with the magazine cover
    s3 = image_slide_html(
        3, False,
        "The other<br>direction.",
        "img-pastors-cover.jpg",
        "India Today, November 14, 2022. Cover story on the growth of "
        "charismatic Christian ministries in Punjab. Reproduced for commentary.",
        [
            "While one system courted the diaspora, another worked the same "
            "population from the opposite side. Healing. Dignity. A way out.",

            "Mainstream coverage treated it as a religious story. The Canadian "
            "part of it is a corporate filing story.",
        ],
        kicker="System two", total=TOTAL, img_h=430,
    )

    # 04 dark - the ministry and the eight-month entity
    s4 = image_slide_html(
        4, True,
        "Eight months.",
        "img-bajinder.jpg",
        "Bajinder Singh. Convicted of rape by a Mohali court on March 28, 2025 "
        "and sentenced to life imprisonment on April 1, 2025. Two further "
        "complaints were filed by other women.",
        [
            "A federal non-profit, corporation number <b>1405947-6</b>, was "
            "incorporated on May 20, 2022 and dissolved on February 14, 2023. "
            "It never filed an annual return.",

            "It listed a director resident in India. Its Canadian address was "
            "a rentable room in a municipal recreation centre in Brampton.",
        ],
        kicker="The filing", total=TOTAL, img_h=360,
    )

    # 05 cream - the mirror
    s5 = slide_html(
        5, False, False,
        "The mirror.",
        [
            '<span class="named">Same country. Same gaps. Opposite methods.</span>'
            '<span class="list">Charity vs non-profit<br>'
            "Decades vs eight months<br>"
            "Returns filed vs never filed<br>"
            "Tax-subsidized vs no reporting at all</span>",

            "One is visible precisely because it files. The other left no trail "
            "precisely because it did not have to.",

            '<span class="q">They are not alleged to be connected. They used '
            "the same gaps independently.</span>",
        ],
        kicker="Side by side", total=TOTAL,
    )

    # 06 dark - the regulatory gap
    s6 = slide_html(
        6, True, False,
        "June 23, 2022.",
        [
            "Bill C-19 let registered charities make qualifying disbursements "
            "straight to organizations that are not Canadian charities, "
            "including foreign ones. The older direction-and-control "
            "requirement came off.",

            "The eight-month non-profit was incorporated one month before that "
            "bill received Royal Assent.",

            "Canada's beneficial ownership registry did not come into force "
            "until January 22, 2024.",

            '<span class="q">What would have to be true for nobody to '
            "notice?</span>",
        ],
        kicker="The gap", total=TOTAL,
    )

    # 07 dark - CTA
    s7 = slide_html(
        7, True, True,
        "Nobody<br>checked.",
        [
            "Part IV was the door. Part V is who walked through it. The "
            "argument underneath both belongs to Santbir Singh.",

            "Sources: the CRA complaint, Sciences Po CERI, federal corporate "
            "records, and court reporting from India. Every figure is "
            "attributed on the Substack.",

            '<span class="divider"></span>'
            '<span class="q">Full sourced series on Substack. Link in bio.'
            "<br>@projectaananta</span>",
        ],
        brand_text=BRAND, total=TOTAL,
    )

    for i, html in enumerate([s1, s2, s3, s4, s5, s6, s7], start=1):
        p = OUT / f"slide-{i:02d}.html"
        p.write_text(html, encoding="utf-8")
        print("wrote", p.name, len(html), "bytes")


if __name__ == "__main__":
    build()

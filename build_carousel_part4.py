#!/usr/bin/env python3
"""
No Place / Part IV - "The Door We Left Open"

Carousel A from the master assembly brief: Santbir Singh's caste
argument. The internal story. Credits Santbir by name on the hook and
the CTA; his scholarship is the foundation and the deck frames it, it
does not rewrite it.

Slide 02 carries Kirpal Singh's depiction of Baba Bota Singh and Baba
Garja Singh, credited in the caption as the user specified.
"""

import pathlib

from build_carousel import slide_html
from layout_image import image_slide_html

HERE = pathlib.Path(__file__).parent
OUT = HERE / "slides_part4"
TOTAL = 7
BRAND = "NO PLACE / PART IV"


def build():
    OUT.mkdir(parents=True, exist_ok=True)

    # 01 cream - the number
    s1 = slide_html(
        1, False, True,
        "One in three.",
        [
            "One in three Sikhs in Punjab is Scheduled Caste. "
            "<b>5,390,484</b> of 16,004,754. Census of India, 2011.",

            "Santbir Singh asks the question most of us step around. Not why "
            "people leave. What they were leaving.",

            '<span class="q">What kind of Panth have we built where leaving '
            "appears to promise dignity?</span>",
        ],
        brand_text=BRAND, total=TOTAL,
    )

    # 02 dark - the historical counter-record, with the Kirpal Singh painting
    s2 = image_slide_html(
        2, True,
        "They shared power.",
        "img-bota-garja.jpg",
        "Baba Bota Singh and Baba Garja Singh fighting, artistic depiction by "
        "Kirpal Singh.",
        [
            "Baba Garja Singh was Ranghreta. He stood beside Baba Bota Singh in "
            "one of the most celebrated assertions of Khalsa sovereignty.",

            "Bhai Bir Singh Ranghreta commanded one of the five principal "
            "jathas of the Taruna Dal. Thirteen hundred cavalry.",

            "Three of the Panj Piare came from marginalized castes.",
        ],
        kicker="The record", total=TOTAL, img_h=372,
    )

    # 03 cream - what it looks like now
    s3 = slide_html(
        3, False, False,
        "Eighty and five.",
        [
            "<b>80%</b> of SGPC administrative positions are held by Jat Sikhs. "
            "<b>5%</b> by Mazhabi Sikhs.",

            "In 41 of 51 villages studied, oppressed-caste communities had "
            "built their own Gurdwaras. Not because they wanted to leave. "
            "Because they were humiliated in the ones that already existed.",

            '<span class="q">The early Khalsa shared command. Three centuries '
            "later, the Panth treats inclusion as generosity.</span>",
        ],
        kicker="Now", total=TOTAL,
    )

    # 04 dark - the diaspora
    s4 = slide_html(
        4, True, False,
        "It boarded<br>the plane.",
        [
            "Caste did not stay in Punjab.",

            "In Dhanda's research, all twelve British Dalit Sikhs interviewed "
            "reported caste-related bullying at school.",

            "Separate lines. Separate halls. Separate Gurdwaras. Carried across "
            "an ocean and rebuilt on arrival.",
        ],
        kicker="The diaspora", total=TOTAL,
    )

    # 05 cream - the vacuum
    s5 = slide_html(
        5, False, False,
        "A door<br>left open.",
        [
            "When an institution withholds dignity, something else offers it. "
            "That is not a mystery. That is a vacancy.",

            "Santbir is explicit, and so is this: it is not a failure of Sikhi. "
            "It is a failure of Sikhs.",

            '<span class="q">Before asking why someone left, ask whether we '
            "abandoned them first.</span>",
        ],
        kicker="The vacuum", total=TOTAL,
    )

    # 06 dark - the question
    s6 = slide_html(
        6, True, False,
        "What we owe<br>our own.",
        [
            "The first generations of the Khalsa did not extend inclusion. They "
            "shared command. There is a difference, and everyone on the "
            "receiving end can feel it.",

            "One in three. Eighty and five. Forty-one of fifty-one.",

            '<span class="q">What would the Panth have to look like for nobody '
            "to need somewhere else to go?</span>",
        ],
        kicker="The question", total=TOTAL,
    )

    # 07 cream - CTA, credit Santbir
    s7 = slide_html(
        7, False, True,
        "Read Santbir.",
        [
            "This carousel frames an argument that is not ours. Santbir Singh, "
            "<b>A Panth Moving in the Wrong Direction</b>, published in Inqlab. "
            "The scholarship is his. Go read it in full.",

            "Figures via Census of India 2011, Jodhka 2002, Ram 2007, and "
            "Dhanda, as cited in his piece.",

            "Part V asks who walked through the door we left open.",

            '<span class="q">Full series on Substack. Link in bio.'
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

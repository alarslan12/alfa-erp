"""Generate ALFA ERP Windows app icons for both editions.

Build-time only; Pillow is not required on user PCs.
Output: multi-resolution Windows ICO plus PNG files, under assets/icons.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[1] / "assets" / "icons"
S = 1024


def rounded_logo(accent, owner=False):
    # Transparent outside: natural Windows icon silhouette and no white box.
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    shade = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.rounded_rectangle((85, 78, 944, 946), radius=205, fill=(4, 11, 28, 125))
    shade = shade.filter(ImageFilter.GaussianBlur(43))
    base.alpha_composite(shade)

    face = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    fp = face.load()
    for y in range(S):
        t = y / (S - 1)
        for x in range(S):
            # Deep blue shifting to midnight, with faint upper-left radiance.
            glow = max(0.0, 1.0 - ((x - 190) ** 2 + (y - 130) ** 2) ** 0.5 / 950)
            fp[x, y] = (int(15 + 16 * (1 - t) + 12 * glow),
                         int(27 + 24 * (1 - t) + 15 * glow),
                         int(51 + 29 * (1 - t) + 23 * glow), 255)
    mask = Image.new("L", (S, S))
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((68, 56, 956, 944), radius=193, fill=255)
    face.putalpha(mask)
    base.alpha_composite(face)

    draw = ImageDraw.Draw(base, "RGBA")
    draw.rounded_rectangle((76, 64, 948, 936), radius=186,
                           outline=(139, 176, 218, 122), width=10)
    draw.line([(192, 150), (793, 150)], fill=(236, 245, 255, 27), width=12)
    # Strong geometric A letterform: two sharp white diagonal pillars.
    draw.polygon([(226, 741), (423, 283), (515, 283), (315, 741)],
                 fill=(252, 254, 255, 255))
    draw.polygon([(423, 283), (516, 283), (777, 741), (669, 741)],
                 fill=(252, 254, 255, 255))
    draw.rounded_rectangle((330, 551, 665, 629), radius=29,
                           fill=(*accent, 255))
    # Quiet double page-lines grounding the A as a business/operations mark.
    draw.rounded_rectangle((270, 799, 754, 816), radius=8,
                           fill=(*accent, 180))
    draw.rounded_rectangle((344, 844, 682, 858), radius=7,
                           fill=(226, 238, 251, 116))
    if owner:
        # Gold diamond / management insignia.
        draw.ellipse((728, 186, 866, 324), fill=(10, 27, 50, 255),
                     outline=(*accent, 255), width=14)
        draw.polygon([(797, 209), (817, 258), (797, 300), (777, 258)],
                     fill=(*accent, 255))
    else:
        # Cyan status mark for the operational edition.
        draw.ellipse((737, 196, 857, 316), fill=(12, 33, 51, 255),
                     outline=(*accent, 255), width=13)
        draw.ellipse((781, 241, 813, 273), fill=(*accent, 255))
    return base


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for edition, color, owner in (
        ("personel", (57, 215, 226), False),
        ("yonetici", (255, 187, 81), True),
    ):
        icon = rounded_logo(color, owner)
        icon.resize((512, 512), Image.Resampling.LANCZOS).save(OUT / f"alfa_{edition}.png")
        icon.save(OUT / f"alfa_{edition}.ico",
                  format="ICO",
                  sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                         (64, 64), (128, 128), (256, 256)])
        print(f"ALFA ERP {edition}: multi-size Windows icon ready")


if __name__ == "__main__":
    main()

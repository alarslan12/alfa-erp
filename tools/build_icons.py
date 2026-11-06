"""Build ALFACOPYCENTER edition icons from the approved transparent brand assets.

Run on the Windows build runner, not on customer machines. The five PNG
sources remain read-only; the generated ICO files are build products.
"""
from pathlib import Path
from PIL import Image

BASE = Path(__file__).resolve().parents[1]
BRAND = BASE / "assets" / "branding"
OUT = BASE / "assets" / "icons"
ICONS = {
    "owner": "alfa_yonetici",
    "staff": "alfa_personel",
    "banner": "alfa_banner",
    "print": "alfa_print",
    "company": "alfa_company",
}
SIZES = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for source, target in ICONS.items():
        path = BRAND / (source + ".png")
        if not path.is_file():
            raise FileNotFoundError(f"Missing brand source: {path}")
        with Image.open(path) as input_image:
            base = input_image.convert("RGBA")
            if base.size != (256,256):
                base.thumbnail((256,256),Image.Resampling.LANCZOS)
                fitted = Image.new("RGBA",(256,256),(0,0,0,0))
                fitted.alpha_composite(
                    base,((256-base.width)//2,(256-base.height)//2))
                base = fitted
            base.save(OUT/(target + ".png"),optimize=True)
            base.save(OUT/(target + ".ico"),format="ICO",sizes=SIZES)
        print(f"ALFACOPYCENTER {source}: 256px transparent icon and ICO ready")


if __name__ == "__main__":
    main()

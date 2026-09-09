"""Generate the multi-resolution TajikLang Studio icon used by Electron."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "studio-electron" / "assets" / "tajiklang.ico"


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, 238, 238), radius=56, fill="#173b3a")
    draw.rounded_rectangle((29, 29, 227, 227), radius=46, fill="#36b890")
    # A deliberately geometric Tajik "Т"; legible at 16px and 256px alike.
    draw.rounded_rectangle((70, 67, 186, 91), radius=10, fill="#edfff9")
    draw.rounded_rectangle((113, 84, 143, 185), radius=10, fill="#edfff9")
    draw.rounded_rectangle((82, 173, 174, 197), radius=10, fill="#edfff9")
    image.save(TARGET, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(TARGET)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

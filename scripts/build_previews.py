"""README 掲載用プレビュー画像を生成する（``docs/previews/*.png``）。

本家 ``basis/scripts/build_previews.py`` と同じ運用: 組版仕様を変えたら本スクリプトで
プレビューを再生成し、同じコミットに含める。手で PNG を置かない。

使い方:
    python scripts/build_previews.py
"""
from __future__ import annotations

from pathlib import Path

from typeset import Font, render, to_png

OUT = Path(__file__).resolve().parent.parent / "docs" / "previews"
BG = "#f4f1ea"

# (ファイル名, 式, セル px)
PREVIEWS: list[tuple[str, str, int]] = [
    ("hero",
     r"\left\{ \frac{x^2 - 1}{x - 1} \right\} \left| x \right| \sqrt{x^{2n}+1} "
     r"\sqrt{\frac{a}{b}} \left[ \matrix{a & b \\ c & d} \right] \\ "
     r"\limits{Σ}{i=1}{n} a_i x^{ab} = X \div 23 + 10", 3),
    ("frac", r"\frac{a+b}{2} = \frac{1}{\frac{1}{x} + \frac{1}{y}}", 4),
    ("script", r"x^2 + x^a + a_i + a_2 \, e^{i\pi}", 4),
    ("sqrt", r"\sqrt{2} \sqrt{x^{2n}+1} \sqrt{\frac{a}{\frac{b}{c}}}", 4),
    ("delim",
     r"\left( \frac{1}{2} \right) \left[ \frac{a}{\frac{b}{c}} \right] "
     r"\left\{ \frac{x^2 - 1}{x - 1} \right\} \left| \frac{a}{\frac{b}{c}} \right| (x)", 4),
    ("limits", r"\limits{Σ}{k=0}{m} a_k = \limits{Π}{i=1}{n} b_i", 4),
    ("matrix", r"\left[ \matrix{1 & 0 & a \\ 0 & 1 & b} \right] \left| \matrix{a & b \\ c & d} \right|", 4),
    ("lines", r"X \div 23 = 10 \\ 28 + X = 63 \\ 50 \times 47 = X", 4),
]


def main() -> None:
    font = Font()
    OUT.mkdir(parents=True, exist_ok=True)
    for stem, expr, cell in PREVIEWS:
        (OUT / f"{stem}.png").write_bytes(to_png(render(expr, font, cell, bg=BG)))
        print(f"  {stem}.png  ← {expr}")


if __name__ == "__main__":
    main()

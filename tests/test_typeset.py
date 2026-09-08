"""typeset.py の最小セルフチェック（``python tests/test_typeset.py`` または pytest）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from typeset import U, Font, layout, parse, render, to_png  # noqa: E402

FONT = Font()


def test_parse_script_and_frac() -> None:
    assert parse("x^2_i") == ("row", [("script", ("char", "x"), ("char", "2"), ("char", "i"))])
    assert parse(r"\frac{a}{b}")[1][0][0] == "frac"
    assert parse(r"a \\ b")[1][1] == ("nl",)


def test_layout_shapes() -> None:
    row = layout(FONT, parse("a+b"))
    assert row.w > 3 * FONT.glyph("a").w          # OP_GAP が入っている
    frac = layout(FONT, parse(r"\frac{1}{2}"))
    assert frac.a > FONT.axis and frac.d > 0      # 分子が軸の上、分母が下
    two = layout(FONT, parse(r"a \\ b"))
    assert two.d > FONT.glyph("b").h              # 2 行目がベースラインより下
    big = layout(FONT, parse(r"\left(\frac{1}{2}\right)"))
    assert big.h >= frac.h
    paren = big.items[0][3].items[0][3]           # row → delim → 左括弧
    rects = [it for it in paren.items if it[0] == "rect"]
    xl, xr = FONT.stem_span("parenleft", 330.0)
    assert len(rects) == 1 and abs(rects[0][3] - (xr - xl)) < 1e-6   # 延長片の幅 = 断面幅（線幅不変）
    assert 100 < xr - xl < 200                                        # 括弧のステム幅相当
    c1, c2 = FONT.cuts("braceleft")                                   # 波括弧は突起（y≈170–270）を避けて 2 箇所
    assert 100 < c1 < 170 and 270 < c2 < 570
    assert len(FONT.cuts("parenleft")) == len(FONT.cuts("radical")) == 1


def test_grid_quantized() -> None:
    row = layout(FONT, parse("ax+1"))
    for dx, _dy, s, b in row.items:                   # インク左端がセル境界に乗る
        assert abs((dx + s * b.lsb) / U - round((dx + s * b.lsb) / U)) < 1e-6
    frac = layout(FONT, parse(r"\frac{1}{2}")).items[0][3]
    _, _x, y, w, h = next(it for it in frac.items if it[0] == "rect")
    assert all(abs(v / U - round(v / U)) < 1e-6 for v in (y, w, h))   # 分数バーもセル整数


def test_real_script_glyphs_used() -> None:
    script = layout(FONT, parse("x^2")).items[0][3]
    _, _, _, sup = script.items[1]
    assert sup.items[0][3].char == "²"            # 実グリフ置換
    assert "scale(" not in render(r"x^2 + y_1", FONT)      # 実グリフのみなら無縮小
    # 実グリフが無い字は 50% 縮小し、実グリフと同じ帯（上付き 28–48 / 下付き −12–8 セル）に乗る
    sup_a = layout(FONT, parse("x^a")).items[0][3].items[1][3]
    assert abs(sup_a.a - 28 * U - 0.5 * FONT.glyph("a").a) < 1 and abs(sup_a.d) < 1e-6
    sub_i = layout(FONT, parse("x_i")).items[0][3].items[1][3]
    assert abs(sub_i.d - 12 * U) < 1e-6


def test_missing_glyph_raises() -> None:
    try:
        layout(FONT, parse("∑"))
    except ValueError as e:
        assert "U+2211" in str(e)
    else:
        raise AssertionError("未収録字で ValueError が出ない")


def test_render_outputs() -> None:
    svg = render(r"X \div 23 = 10", FONT, bg="white")
    assert "<path" in svg and "CC BY 4.0" in svg
    assert to_png(svg)[:8] == b"\x89PNG\r\n\x1a\n"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)

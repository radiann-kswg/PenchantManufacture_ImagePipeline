"""PenchantManufacture グリフによる多段数式の画像組版（最小実装）。

本家 ``basis/`` のフォント実メトリクス（advance・GPOS カーニング・インク境界）と
アウトラインだけを入力に、TeX 風の式文字列を 1 枚の SVG/PNG に組む。
デカール PNG（``basis/dist/``）は使わない（AGENTS.md「入力の契約」）。

対応する記法（最小セット）:
    a+b  x^2  x_i            文字・上付き・下付き（実グリフがあれば置換、無ければ 50% 縮小で同位置）
    \\frac{a}{b}              分数（バーは hyphen のステム幅・数式軸に合わせる）
    \\sqrt{x}                 根号（√ の縦画を延長片で伸ばし＋上線）
    \\left( ... \\right)      可変高括弧（( ) [ ] { } | を上端／下端に分割し延長片で補完）
    \\limits{Σ}{i=1}{n}       大型演算子の上下引数（上＝下付き字・下＝上付き字で組む）
    \\matrix{a & b \\\\ c & d}  行列
    a = b \\\\ c = d           複数行
    \\times \\div \\pm \\leq \\geq \\neq \\infty \\alpha … \\omega  記号・ギリシャ

座標系はフォント単位（1000 upm・Y 上向き）で組み、最後に 1 つの matrix で px へ落とす
（``generate_roman.py`` と同じ変換）。縦位置はフォント登録メトリクスをそのまま用い、
組版側でベースラインを動かさない。間隔・段組み・延長片・出力 px は字面の設計グリッド
（28×40 セル、1 セル = 16.5 units）の整数倍に量子化する（``U`` / ``q``）。

著作権者: RadianN_kswg / ラジアン（柏木主税） / ライセンス: CC BY 4.0

使い方:
    python scripts/typeset.py "\\frac{a+b}{2} = x^2" -o out.png
    python scripts/typeset.py "X \\div 23 = 10" -o q.png --cell 4 --bg white
    python scripts/typeset.py "\\sqrt{x^2+y^2}" -o out.svg
"""
from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from io import BytesIO
from itertools import accumulate, count
from pathlib import Path
from xml.sax.saxutils import escape

import click
from fontTools import ttLib
from fontTools.misc.bezierTools import segmentSegmentIntersections
from fontTools.pens.basePen import decomposeQuadraticSegment
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen

ROOT = Path(__file__).resolve().parent.parent
BASIS = ROOT / "basis"
sys.path.insert(0, str(BASIS / "scripts"))
from generate_roman import load_kern_pairs  # noqa: E402  本家のカーニング読み取りを共用

FONT_PATH = BASIS / "assets" / "fonts" / "PenchantManufacture.otf"
CREDIT = "PenchantManufacture by RadianN_kswg / ラジアン（柏木主税） / CC BY 4.0"

# ── 設計グリッド ──
# PenchantManufacture の字面は 28×40 セルのグリッドに量子化して設計されている
# （cap height 660 = 40 セル、最大字幅 462 = 28 セル、ステム幅 99 = 6 セル）。
# 組版側の間隔・段組み・延長片・出力 px もすべてこの 1 セル = 16.5 units を単位にする。
U = 660 / 40          # 1 セル（フォント units）


def q(v: float) -> float:
    """セル単位へ丸める。"""
    return round(v / U) * U


def q_up(v: float) -> float:
    """セル単位へ切り上げる。"""
    return math.ceil(v / U - 1e-9) * U


# ── 組版定数（セル数） ──
OP_GAP = 11 * U       # 二項演算子・関係子の前後空き
THIN = 10 * U         # \, の空き
LINE_GAP = 12 * U     # 複数行の行間（前行 descent と次行 ascent の間）
FRAC_GAP = 6 * U      # 分数バーと分子・分母の間（＝ステム幅 1 本分）
# 拡大縮小は上付き／下付きの代替にのみ許容する。フォント収録の上付き字（⁰–⁹ ⁿ ⁱ …）は
# 高さ 20 セル＝本体の 50% で、ベースラインが x-height（28 セル）、下付き字は −12 セルに
# 置かれている。実グリフの無い字はこれに合わせて 50% 縮小し同じ位置へ置く。
SCRIPT_SCALE = 0.5
SUP_RAISE = 28 * U    # 縮小上付きのベースライン（実上付き字の下端 = x-height）
SUB_DROP = 12 * U     # 縮小下付きのベースライン（実下付き字の下端 = ディセンダ）
LIMIT_GAP = 4 * U     # 大型演算子と上下引数の間
COL_GAP = 20 * U      # 行列の列間
ROW_GAP = 10 * U      # 行列の行間
MARGIN = 8 * U        # 画像外周余白

BINARY = set("+-=×÷±∓≤≥≠≈≡∈∉⊂⊃⊆⊇∧∨∩∪∝→")
FALLBACK = {"−": "-"}   # フォントに無い字の代替（U+2212 MINUS → hyphen）

_GREEK = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi "
          "omicron pi rho sigma tau upsilon phi chi psi omega").split()
COMMANDS: dict[str, str] = {
    "times": "×", "div": "÷", "pm": "±", "mp": "∓", "cdot": "·",
    "leq": "≤", "geq": "≥", "neq": "≠", "approx": "≈", "equiv": "≡",
    "infty": "∞", "partial": "∂", "nabla": "∇", "in": "∈", "notin": "∉",
    "cup": "∪", "cap": "∩", "land": "∧", "lor": "∨", "forall": "∀", "exists": "∃",
    "propto": "∝", "therefore": "∴", "because": "∵", "ldots": "…", "cdots": "…",
    "sum": "∑", "prod": "∏", "int": "∫",   # C2 大型演算子（本家 OTF 収録待ち）
}
COMMANDS.update({g: chr(0x3B1 + i + (1 if i >= 17 else 0)) for i, g in enumerate(_GREEK)})
COMMANDS.update({g.capitalize(): chr(0x391 + i + (1 if i >= 17 else 0))
                 for i, g in enumerate(_GREEK)})

SUPER = dict(zip("0123456789+-=()ni", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ"))
SUB = dict(zip("0123456789+-=()n", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₙ"))


# ── レイアウトボックス ──
@dataclass
class Box:
    """フォント単位のボックス。``a``/``d`` はベースラインからの上・下の広がり（≥0）。"""

    w: float = 0.0
    a: float = 0.0
    d: float = 0.0
    glyph: str | None = None        # グリフ名（カーニング用。単独グリフのみ）
    char: str | None = None
    lsb: float = 0.0                # インク左端（グリフのみ。合成ボックスは 0）
    items: list = field(default_factory=list)   # ("path", d) | ("rect", x, y, w, h) | (dx, dy, s, Box)

    @property
    def h(self) -> float:
        return self.a + self.d

    def put(self, dx: float, dy: float, box: Box, s: float = 1.0) -> None:
        """子ボックスを (dx, dy) に倍率 s で置き、自身の広がりを拡張する（s≠1 は上付き／下付き代替のみ）。

        位置はセルに量子化する。横はインク左端がセル境界に乗るよう lsb を差し引いて丸める
        （advance との差は最大 0.5 セル）。縦はフォントの字面が既にセルに乗っているので
        原点をそのまま丸める。
        """
        dx = q(dx + s * box.lsb) - s * box.lsb
        dy = q(dy)
        self.items.append((dx, dy, s, box))
        self.w = max(self.w, dx + s * box.w)
        self.a = max(self.a, dy + s * box.a)
        self.d = max(self.d, s * box.d - dy)

    def rect(self, x: float, y: float, w: float, h: float) -> None:
        self.items.append(("rect", x, y, w, h))
        self.w = max(self.w, x + w)
        self.a = max(self.a, y + h)
        self.d = max(self.d, -y)


def hshift(box: Box, dx: float) -> Box:
    """ボックスを右へ dx ずらした親ボックスを返す。"""
    out = Box()
    out.put(dx, 0, box)
    return out


# ── フォント ──
class Font:
    """PenchantManufacture の実メトリクス・アウトライン・カーニングの読み取り口。"""

    def __init__(self, path: Path = FONT_PATH) -> None:
        self.tt = ttLib.TTFont(str(path))
        self.cmap = self.tt.getBestCmap()
        self.gs = self.tt.getGlyphSet()
        self.hmtx = self.tt["hmtx"].metrics
        self.kern = load_kern_pairs(self.tt)
        self.upm: int = self.tt["head"].unitsPerEm
        hy = self.bounds(self.name("-"))
        self.rule = q(hy[3] - hy[1])              # 分数バー等の線幅 = hyphen のステム幅（6 セル）
        self.axis = q((hy[1] + hy[3]) / 2)        # 数式軸 = hyphen のインク中心（17 セル）

    def has(self, ch: str) -> bool:
        return ord(FALLBACK.get(ch, ch)) in self.cmap

    def name(self, ch: str) -> str:
        ch = FALLBACK.get(ch, ch)
        try:
            return self.cmap[ord(ch)]
        except KeyError:
            raise ValueError(f"フォント未収録の字: {ch!r} (U+{ord(ch):04X})") from None

    @lru_cache(maxsize=None)
    def bounds(self, g: str) -> tuple[float, float, float, float]:
        pen = BoundsPen(self.gs)
        self.gs[g].draw(pen)
        return pen.bounds or (0.0, 0.0, 0.0, 0.0)

    @lru_cache(maxsize=None)
    def path(self, g: str) -> str:
        pen = SVGPathPen(self.gs)
        self.gs[g].draw(pen)
        return pen.getCommands()

    def glyph(self, ch: str) -> Box:
        """1 字のボックス（幅 = advance、上下 = インク境界）。縦位置はフォントのまま。"""
        g = self.name(ch)
        x0, y0, _x1, y1 = self.bounds(g)
        box = Box(w=self.hmtx[g][0], a=max(y1, 0.0), d=max(-y0, 0.0), glyph=g, char=ch, lsb=x0)
        if d := self.path(g):
            box.items.append(("path", d))
        return box

    @lru_cache(maxsize=None)
    def stem_span(self, g: str, y: float) -> tuple[float, float]:
        """高さ ``y`` の水平線とアウトラインの交点から、そこでのインクの x 範囲を返す。"""
        rec = RecordingPen()
        self.gs[g].draw(rec)
        line = ((-1e5, y), (1e5, y))
        xs: list[float] = []
        cur = start = (0.0, 0.0)
        for op, pts in rec.value:
            if op == "moveTo":
                cur = start = pts[0]
                continue
            if op == "closePath" or op == "endPath":
                segs = [(cur, start)] if cur != start else []
            elif op == "qCurveTo":
                segs = [(cur, *q) for q in decomposeQuadraticSegment(pts)]
            else:                                   # lineTo / curveTo
                segs = [(cur, *pts)]
            for seg in segs:
                # 直線同士は無限直線の交点が返るので t1 で線分内に絞る
                xs += [i.pt[0] for i in segmentSegmentIntersections(seg, line)
                       if -1e-6 <= i.t1 <= 1 + 1e-6]
                cur = seg[-1]
        if not xs:
            raise ValueError(f"{g}: y={y:.0f} にインクが無く延長できません")
        return min(xs), max(xs)

    @lru_cache(maxsize=None)
    def cuts(self, g: str) -> list[float]:
        """延長片を差し込む高さ（分割位置）を字形から決める。

        断面が一定＝垂直ステムの区間を 4 unit 刻みで探し、その中点で切る。
        最長ステムと同じ断面の区間がもう 1 つあれば（{ } | のように中央に意匠がある字）
        長い順に 2 箇所、無ければ最長の 1 箇所。意匠や端の斜め部を切らずに済む。
        """
        _x0, y0, _x1, y1 = self.bounds(g)
        runs: list[list] = []                       # [断面, 開始y, 終了y]
        y = y0 + 2
        while y < y1 - 2:
            try:
                span = tuple(round(v) for v in self.stem_span(g, y))
            except ValueError:
                span = None
            if runs and runs[-1][0] == span:
                runs[-1][2] = y
            else:
                runs.append([span, y, y])
            y += 4
        runs = [r for r in runs if r[0]]
        best = max(runs, key=lambda r: r[2] - r[1])
        same = sorted((r for r in runs if r[0] == best[0]), key=lambda r: r[1] - r[2])[:2]
        return sorted((r[1] + r[2]) / 2 for r in same)

    def delim(self, ch: str, height: float, center: float) -> Box:
        """可変高括弧・根号：字を上端／下端（中央意匠がある字はそれも）に分割し、間を延長片で埋める。

        分割位置（``cuts``）のインク断面と同じ幅の矩形を差し込むので、高さを変えても
        線幅は元のグリフのまま。中央意匠は伸長後の中心に来るよう上下の延長量を配分する。
        インク中心を ``center`` に合わせる。
        """
        g = self.glyph(ch)
        _x0, y0, _x1, y1 = self.bounds(g.glyph)
        ext = q_up(height) - q(y1 - y0)             # 延長量はセルの整数倍
        out = Box()
        if ext <= 0:
            out.put(0, center - (y0 + y1) / 2, g)
            return out
        cuts = self.cuts(g.glyph)
        if len(cuts) == 2:                          # 中央意匠を伸長後の中心へ
            lo = min(max(q(y0 + (q(y1 - y0) + ext) / 2 - sum(cuts) / 2), 0.0), ext)
            gaps = [lo, ext - lo]
        else:
            gaps = [ext]
        offs = [0.0, *accumulate(gaps)]
        eps = 3.0                                    # AA の継ぎ目隠しの重なり
        base = q(center - (y0 + y1 + ext) / 2)
        bands = zip([y0 - 1] + cuts, cuts + [y1 + 1])   # 各断片のクリップ範囲（下→上）
        for i, (lo, hi) in enumerate(bands):
            piece = Box(w=g.w, a=g.a, d=g.d, items=[("clip", lo, hi, g)])
            out.put(0, base + offs[i], piece)
        for i, cut in enumerate(cuts):
            xl, xr = self.stem_span(g.glyph, cut)
            out.rect(xl, base + cut + offs[i] - eps, xr - xl, gaps[i] + 2 * eps)
        out.w = g.w
        return out


# ── 構文解析 ──
_TOKEN = re.compile(r"\\[A-Za-z]+|\\.|[{}^_&]|\s+|.", re.S)

Node = tuple  # ("char", c) | ("row", [..]) | ("frac", n, d) | ("script", base, sup, sub) | ...


def tokenize(src: str) -> list[str]:
    return [t for t in _TOKEN.findall(src) if not t.isspace()]


class Parser:
    def __init__(self, src: str) -> None:
        self.toks = tokenize(src)
        self.i = 0

    def peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def next(self) -> str:
        if self.i >= len(self.toks):
            raise ValueError("式が途中で終わっています")
        self.i += 1
        return self.toks[self.i - 1]

    def arg(self) -> Node:
        """``{...}`` または 1 トークンを 1 引数として読む。"""
        t = self.next()
        if t == "{":
            nodes = self.seq()
            if self.next() != "}":
                raise ValueError("'}' がありません")
            return ("row", nodes)
        return self.atom(t)

    def atom(self, t: str) -> Node:
        if t == "\\\\":
            return ("nl",)
        if t == "\\,":
            return ("space", THIN)
        if t == "\\ ":
            return ("space", None)
        if t == "\\frac":
            return ("frac", self.arg(), self.arg())
        if t == "\\sqrt":
            return ("sqrt", self.arg())
        if t == "\\limits":
            return ("limits", self.arg(), self.arg(), self.arg())
        if t == "\\matrix":
            return ("matrix", self.arg())
        if t == "\\left":
            left = self.next()
            inner = self.seq()
            if self.next() != "\\right":
                raise ValueError("\\right がありません")
            return ("delim", left, ("row", inner), self.next())
        if t.startswith("\\"):
            name = t[1:]
            if name not in COMMANDS:
                raise ValueError(f"未対応のコマンド: {t}")
            return ("char", COMMANDS[name])
        if t == "&":
            return ("amp",)
        if t in "{}^_":
            raise ValueError(f"'{t}' の位置が不正です")
        return ("char", t)

    def seq(self) -> list[Node]:
        nodes: list[Node] = []
        while (t := self.peek()) not in (None, "}", "\\right"):
            self.next()
            if t in "^_":
                if not nodes:
                    raise ValueError(f"'{t}' の前に字がありません")
                base = nodes.pop()
                if base[0] != "script":
                    base = ("script", base, None, None)
                arg = self.arg()
                base = (("script", base[1], arg, base[3]) if t == "^"
                        else ("script", base[1], base[2], arg))
                nodes.append(base)
            else:
                nodes.append(self.atom(t))
        return nodes


def parse(src: str) -> Node:
    p = Parser(src)
    nodes = p.seq()
    if p.peek() is not None:
        raise ValueError(f"余分な '{p.peek()}' があります")
    return ("row", nodes)


# ── レイアウト ──
def _split(nodes: list[Node], sep: str) -> list[list[Node]]:
    parts: list[list[Node]] = [[]]
    for n in nodes:
        (parts.append([]) if n[0] == sep else parts[-1].append(n))
    return parts


def _chars(node: Node) -> str | None:
    """行が単純な文字列だけならその文字列を返す（実グリフ置換の判定用）。"""
    nodes = node[1] if node[0] == "row" else [node]
    if all(n[0] == "char" for n in nodes):
        return "".join(n[1] for n in nodes)
    return None


def _small(font: Font, node: Node, table: dict[str, str], dy: float) -> Box:
    """上付き／下付き：実グリフがあれば置換、無ければ 50% 縮小して実グリフと同じ位置に置く。"""
    s = _chars(node)
    if s is not None and all(c in table and font.has(table[c]) for c in s):
        return hbox(font, [("char", table[c]) for c in s])
    out = Box()
    out.put(0, dy, layout(font, node), SCRIPT_SCALE)
    return out


def hbox(font: Font, nodes: list[Node]) -> Box:
    """横並び。単独グリフ同士には GPOS カーニング、演算子の前後には OP_GAP。"""
    out = Box()
    x = 0.0
    prev: Box | None = None
    boxes = [layout(font, n) for n in nodes]
    for i, b in enumerate(boxes):
        is_op = b.char in BINARY and 0 < i < len(boxes) - 1
        if prev is not None and prev.glyph and b.glyph:
            x += font.kern.get((prev.glyph, b.glyph), 0)
        if is_op:
            x += OP_GAP
        out.put(x, 0, b)
        x += b.w + (OP_GAP if is_op else 0)
        prev = b
    out.w = x
    return out


def vstack(font: Font, rows: list[Box], gap: float, align: str = "center") -> Box:
    """行を縦に積む。1 行目のベースラインを親のベースラインにする。"""
    out = Box()
    width = max((r.w for r in rows), default=0.0)
    y = 0.0
    for i, r in enumerate(rows):
        if i:
            y -= rows[i - 1].d + gap + r.a
        dx = (width - r.w) / 2 if align == "center" else 0.0
        out.put(dx, y, r)
    out.w = width
    return out


def layout(font: Font, node: Node) -> Box:
    kind = node[0]
    if kind == "char":
        return font.glyph(node[1])
    if kind == "space":
        return Box(w=node[1] if node[1] is not None else font.hmtx[font.name(" ")][0])
    if kind == "row":
        lines = _split(node[1], "nl")
        if len(lines) > 1:
            return vstack(font, [hbox(font, ln) for ln in lines], LINE_GAP)
        return hbox(font, lines[0])
    if kind == "script":
        _, base, sup, sub = node
        out = Box()
        out.put(0, 0, b := layout(font, base))
        x = b.w
        w = 0.0
        if sup is not None:
            sb = _small(font, sup, SUPER, SUP_RAISE)
            out.put(x, 0, sb)
            w = sb.w
        if sub is not None:
            sb = _small(font, sub, SUB, -SUB_DROP)
            out.put(x, 0, sb)
            w = max(w, sb.w)
        out.w = x + w
        return out
    if kind == "frac":
        num, den = layout(font, node[1]), layout(font, node[2])
        r, ax = font.rule, font.axis
        width = q_up(max(num.w, den.w)) + 2 * r
        out = Box()
        out.rect(0, q(ax - r / 2), width, r)
        out.put((width - num.w) / 2, ax + r / 2 + FRAC_GAP + num.d, num)
        out.put((width - den.w) / 2, ax - r / 2 - FRAC_GAP - den.a, den)
        return out
    if kind == "sqrt":
        inner = layout(font, node[1])
        r = font.rule
        g = font.name("√")
        _x0, y0, x1, y1 = font.bounds(g)
        top = inner.a + 2 * r
        rad = font.delim("√", top + inner.d, (top - inner.d) / 2)   # 縦画を延長片で伸ばす
        # 上線: 太さは根号の横画（＝ステム幅）、根号の縦画右端から始めて頂点の面取りを覆い、
        # 上端を根号のインク上端に揃える（継ぎ目が出ない）
        bar_x = font.stem_span(g, (y0 + y1) / 2)[1]
        x = q_up(x1 + r)
        out = Box()
        out.put(0, 0, rad)
        out.put(x, 0, inner)
        out.rect(bar_x, rad.a - r, q_up(x + inner.w + r) - bar_x, r)
        out.w = q_up(x + inner.w + r)
        return out
    if kind == "delim":
        _, left, inner_node, right = node
        inner = layout(font, inner_node)
        c = (inner.a - inner.d) / 2
        out = Box()
        x = 0.0
        left, right = left.lstrip("\\"), right.lstrip("\\")     # \{ \} も受ける
        for part in (font.delim(left, inner.h, c), inner, font.delim(right, inner.h, c)):
            out.put(x, 0, part)
            x += part.w
        out.w = x
        return out
    if kind == "limits":     # 上引数＝下付き字・下引数＝上付き字（FUTURE_PLAN §3-3 の記載規則）
        _, sym_n, lo_n, hi_n = node
        sym = layout(font, sym_n)
        hi = _small(font, hi_n, SUB, 0)
        lo = _small(font, lo_n, SUPER, 0)
        width = max(sym.w, hi.w, lo.w)
        out = Box()
        out.put((width - hi.w) / 2, sym.a + LIMIT_GAP + hi.d, hi)
        out.put((width - sym.w) / 2, 0, sym)
        out.put((width - lo.w) / 2, -sym.d - LIMIT_GAP - lo.a, lo)
        out.w = width
        return out
    if kind == "matrix":
        rows = [[hbox(font, cell) for cell in _split(ln, "amp")]
                for ln in _split(node[1][1], "nl")]
        ncol = max(len(r) for r in rows)
        colw = [q_up(max((r[j].w for r in rows if j < len(r)), default=0.0)) for j in range(ncol)]
        out = Box()
        y = 0.0
        for i, r in enumerate(rows):
            ra, rd = max(c.a for c in r), max(c.d for c in r)
            if i:
                y -= ROW_GAP + ra
            x = 0.0
            for j, c in enumerate(r):
                out.put(x + (colw[j] - c.w) / 2, y, c)
                x += colw[j] + COL_GAP
            y -= rd
        out.w = sum(colw) + COL_GAP * (ncol - 1)
        # 行列全体を数式軸に中央揃え
        c = Box()
        c.put(0, font.axis - (out.a - out.d) / 2, out)
        c.w = out.w
        return c
    raise ValueError(f"未知のノード: {kind}")


# ── 出力 ──
_CLIP_ID = count()


def _svg_items(box: Box) -> str:
    parts = []
    for it in box.items:
        if it[0] == "path":
            parts.append(f'<path d="{it[1]}"/>')
        elif it[0] == "rect":
            _, x, y, w, h = it
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/>')
        elif it[0] == "clip":                     # y ∈ [lo, hi] の帯だけ描く
            _, lo, hi, b = it
            n = next(_CLIP_ID)
            parts.append(f'<clipPath id="c{n}"><rect x="-9999" y="{lo:.1f}" width="99999" '
                         f'height="{hi - lo:.1f}"/></clipPath>'
                         f'<g clip-path="url(#c{n})">{_svg_items(b)}</g>')
        else:
            dx, dy, s, b = it
            tf = f"translate({dx:.1f},{dy:.1f})" + (f" scale({s})" if s != 1.0 else "")
            parts.append(f'<g transform="{tf}">{_svg_items(b)}</g>')
    return "".join(parts)


def to_svg(box: Box, cell: int, color: str = "#000000", bg: str | None = None,
           title: str = "") -> str:
    """ボックスを 1 枚の SVG にする（フォント単位 → px は外側の matrix 1 つで変換）。

    ``cell`` は 1 セルあたりの px（整数）。セルに乗った座標はすべて整数 px に落ちる。
    """
    s = cell / U
    w = round((q_up(box.w) + 2 * MARGIN) * s)
    h = round((q_up(box.h) + 2 * MARGIN) * s)
    ty = (MARGIN + box.a) * s
    bg_el = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n'
        f"  <title>{escape(title)}</title>\n  <desc>{escape(CREDIT)}</desc>\n"
        f"  {bg_el}\n"
        f'  <g fill="{color}" transform="matrix({s:.6f},0,0,{-s:.6f},{MARGIN * s:.3f},{ty:.3f})">'
        f"{_svg_items(box)}</g>\n</svg>\n"
    )


def to_png(svg: str) -> bytes:
    """SVG → PNG（クレジットを tEXt チャンクに保持）。"""
    import cairosvg
    from PIL import Image, PngImagePlugin

    im = Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode("utf-8"))))
    meta = PngImagePlugin.PngInfo()
    meta.add_text("Author", "RadianN_kswg / ラジアン（柏木主税）")
    meta.add_text("Copyright", CREDIT)
    buf = BytesIO()
    im.save(buf, "PNG", pnginfo=meta)
    return buf.getvalue()


def render(src: str, font: Font | None = None, cell: int = 3, color: str = "#000000",
           bg: str | None = None) -> str:
    """式文字列 → SVG 文字列。``cell`` = 1 セルの px（3 → cap height 120px）。"""
    font = font or Font()
    return to_svg(layout(font, parse(src)), cell, color, bg, title=src)


@click.command()
@click.argument("expr")
@click.option("-o", "--out", type=click.Path(path_type=Path), required=True,
              help="出力先（.png または .svg）")
@click.option("--cell", default=3, show_default=True, type=int,
              help="1 セル（16.5 units）あたりの px。3 → cap height 120px")
@click.option("--color", default="#000000", show_default=True)
@click.option("--bg", default=None, help="背景色（未指定なら透過）")
@click.option("--font", "font_path", default=str(FONT_PATH), show_default=True)
def main(expr: str, out: Path, cell: int, color: str, bg: str | None, font_path: str) -> None:
    """TeX 風の式 EXPR を PenchantManufacture で組版し画像にします。"""
    svg = render(expr, Font(Path(font_path)), cell, color, bg)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".svg":
        out.write_text(svg, encoding="utf-8")
    else:
        out.write_bytes(to_png(svg))
    click.echo(f"{out}  ({CREDIT})")


if __name__ == "__main__":
    main()

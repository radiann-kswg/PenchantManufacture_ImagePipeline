# AGENTS.md — PenchantManufacture_ImagePipeline 共通エージェント指示書

このファイルは **Codex**、**Claude Code**、**GitHub Copilot** が共有する
PenchantManufacture_ImagePipeline リポジトリ固有指示の **唯一の正（SSOT）** です。
`CLAUDE.md` は `@AGENTS.md` の参照入口であり、詳細指示を重複記載しません。

---

## プロジェクト概要

**PenchantManufacture フォントのグリフから、複数行にまたがる数式・技術表記を
1 枚の画像として組版する Bot／アプリ向けパイプライン** です。

上流の `PenchantManufacture_ImageAssets`（本家）はサブモジュール **`basis/`** として取得し、
グリフソース・フォント・命名規則・字形契約は **`basis/AGENTS.md` に準拠**します。
本ファイルには ImagePipeline 固有の差分のみを記載します。

**著作権者**: RadianN_kswg / ラジアン（柏木主税） / **ライセンス**: CC BY 4.0

---

## なぜこのリポジトリが存在するか（責務分界）

本家のカスタム絵文字は **1 行で完結する技術表記**（型番・仕様・単位・図面注記・
化学反応式・1 行に収まる数式）までを担う。**複数行にまたがる組版はカスタム絵文字では
原理的に実現できない**ため、本リポジトリが画像生成で引き取る。

**絵文字で多段組版が成立しない理由**（本家 [basis/docs/GLYPH_EXTENSION_PLAN.md] §0-2）:

1. Misskey の MFM に行間・列揃えの制御機構が無い。
2. Misskey が配信するのは 128px 版で `128 / 21 = 6.095 px/単位` と**非整数**。
   画像側で幅をグリッドへ量子化しても丸め誤差で桁がずれる。
3. ブラウザは CSS 高さ（≒1.5em）で**任意倍率に縮小描画**するため、PNG の幅を何にしても
   レンダリング時点でサブピクセル誤差が入る。列揃えを保証できるのは
   **1 枚の画像に組む方式のみ**＝本リポジトリ。

| 責務 | 担当 |
| --- | --- |
| 1 行の技術表記（絵文字 1 字 1 枚） | **本家** `PenchantManufacture_ImageAssets` |
| 分数の 2 行組版 | **本リポジトリ** |
| 大型演算子の上下引数（∑ の上限・下限） | **本リポジトリ** |
| 行列式・多段数式 | **本リポジトリ** |
| 可変高括弧（上端／下端／延長片） | **本リポジトリ**。「文字ではなく図形」であり本家では作字しない |

---

## 入力の契約（最重要）

**入力は `basis/src/glyphs/` の SVG ＋ フォントの実メトリクスのみ。**

| 使う | 使わない |
| --- | --- |
| `basis/src/glyphs/char_*.svg`（アウトライン化済みパス・409字） | `basis/dist/glyphs_decal/{variant}/*.png` |
| `basis/src/glyphs_roman/roman_*.svg`（合成ローマ数字ソース・54点） | `basis/dist/glyphs_decal_square/{variant}/*.png` |
| `basis/assets/fonts/PenchantManufacture.otf`（advance・GPOS カーニング・OS/2 win 帯） | `basis/dist/glyphs_roman/`, `basis/dist/glyphs_spacer/` |

> 実装（`scripts/typeset.py`）は `src/glyphs/*.svg` と同一のアウトラインを OTF から `SVGPathPen` で
> 直接読む（`generate_roman.py` と同じ経路）。SVG ファイルの解析は行わない（[docs/HANDOFF_PLAN.md] §3）。

**デカール PNG を素材にしてはならない。** デカールは 1 字ごとに外ハロー 10px ＋
キーライン 6px ＋ `CROP_MARGIN` 13px を各辺に持つため、並べると字間にそれが二重に入り、
密な数式で字がくっついて見える。またパディングが実メトリクスを覆い隠し、精密配置ができない。
デカールの質感が必要な場合は、**組版後の合成パスに対して `basis/scripts/generate_decal.py` の
SDF 実装を適用する**（`generate_roman.py` と同じ方式）。

### 既存資産の再利用

`basis/scripts/generate_roman.py` が既に

- フォントの **GPOS カーニングを読んで**合成 SVG（横長 viewBox）を組む
- 合成 SVG に対して `generate_decal.py` の SDF・5 スキーム・シードを**共用**して
  デカール化し、単独グリフと質感・縁取り・配置契約を完全に揃える

を実装している。**多段組版はこの自然な拡張として実装すること。**
新規に組版エンジンを起こす前に必ず `generate_roman.py` を読むこと。

### メトリクスの読み方

| 項目 | 値（v4.0-beta） | 出所 |
| --- | --- | --- |
| Units per em | 1000 | `head.unitsPerEm` |
| OS/2 win 帯 | `usWinAscent 793` / `usWinDescent 198`（帯 991） | 全グリフ共通の縦バンド |
| cap height / x-height | 661 / 462 | |
| ディセンダ下端 | 約 −101（g/j/p/q/y） | |
| advance | **161 通り・111〜1036 units**（量子化されていない） | `hmtx` |
| 配置フレーム | `src/glyphs/*.svg` 冒頭の `<!-- frame x=X0,X1 y=Y0,Y1 -->` | `extract_glyphs.py` が埋め込む。横 = advance ∪ インク、縦 = win 帯 |

- **縦位置はフォント登録メトリクスをそのまま信頼する**（本家 v3.3 以降の契約）。
  組版側でベースラインを動かさないこと。
- 分数バー・括弧の延長片など**フォントに無い図形を描く場合のみ**、線幅を字形の
  ステム幅に合わせて実測から決める（字形契約を目視で壊さないため）。

---

## 権限・ライセンス（最優先）

- **著作権者**：RadianN_kswg / ラジアン（柏木主税）
- **ライセンス**：CC BY 4.0（本家・CJK 版と同一）
- PenchantManufacture フォントのグリフは著作者の独自創作物。
  第三者フォント・商用グリフのグリフパスを流用することを **絶対に行わないこと**。
- **生成画像にクレジット属性を保持すること。** Bot／アプリとして配信する場合、
  出力画像そのものか、Bot のプロフィール・ヘルプ・API レスポンスのいずれかで
  `RadianN_kswg / ラジアン（柏木主税） / CC BY 4.0` を明示する。
- `basis/` 内のファイルは **読み取り専用**。変更は本家リポジトリで行う。

---

## サブモジュール `basis/`

```
PenchantManufacture_ImagePipeline/
├── AGENTS.md                ← 本ファイル（ImagePipeline 固有差分の SSOT）
├── CLAUDE.md                ← Claude Code 互換入口（@AGENTS.md のみ）
├── .github/
│   └── copilot-instructions.md
├── .gitmodules              ← basis → radiann-kswg/PenchantManufacture_ImageAssets (main)
├── basis/                   ← 【サブモジュール】PenchantManufacture_ImageAssets（読み取り専用）
├── scripts/
│   ├── typeset.py           ← 組版本体（TeX 風の式 → SVG/PNG）。CLI 兼ライブラリ
│   └── build_previews.py    ← README 掲載プレビュー（docs/previews/）の再生成
├── tests/test_typeset.py    ← 最小セルフチェック
├── docs/
│   ├── TYPESET_SPEC.md      ← 組版仕様の SSOT（グリッド・各構造の配置規則・実測値）
│   ├── HANDOFF_PLAN.md      ← 引継ぎ資料（未対応タスク・本家連動タスク・決定事項）
│   └── previews/*.png       ← README 掲載画像（build_previews.py の生成物。手で置かない）
├── README.md
├── requirements.txt         ← `-r basis/requirements.txt`
└── LICENSE                  ← CC BY 4.0
```

```bash
git submodule update --init --recursive      # 初回取得
git submodule update --remote basis          # 本家の main へ追従
```

- **`basis/` 内のファイルは変更禁止。** 本家側の修正が必要になったら
  `PenchantManufacture_ImageAssets` リポジトリで行い、こちらは参照コミットを更新する。
- サブモジュール更新は「`git submodule update --remote` ＋ 参照コミットの更新コミット」で行う。
- 本家のスクリプト・仕様を参照する際は常に `basis/` 側のパスを読む。
- **本家に ImagePipeline 向けの分岐を入れさせないこと。** 本家は下流を知らずに
  ビルドできる状態を保つ（本家 [AGENTS.md]「下流プロダクト」節の約束）。

---

## ドキュメントの優先順位

| 文書 | 役割 |
| --- | --- |
| 本ファイル | 責務分界・入力の契約・禁止事項 |
| [docs/TYPESET_SPEC.md] | **組版規則の正**。セル定義（1 セル = 16.5 units）・分数／括弧／根号／上下付きの配置式・実測値 |
| [docs/HANDOFF_PLAN.md] | 未対応タスク、本家 `GLYPH_EXTENSION_PLAN.md` §6 との連動表、決定事項の記録 |
| README.md | 利用者向け。記法一覧とプレビュー |

組版規則を変えるときは **SPEC → 実装 → テスト → `python scripts/build_previews.py`** の順で、
`docs/previews/` の再生成を同じコミットに含める（本家の README プレビュー運用と同じ）。
画素が変わらない再生成（実行環境の違いで PNG のバイト列だけが変わる）はコミットに含めない。

## 実装の指針

- 組版は `scripts/typeset.py` に集約されている（解析 → `Box` レイアウト → SVG → PNG）。
  新しい構造（環境）を足すときは `layout()` に分岐を 1 つ足し、配置式を [docs/TYPESET_SPEC.md] §4 に書く。
- **グリフの拡大縮小は上付き／下付きの 50% 代替以外で行わない。** 高さが要る図形（括弧・根号）は
  `Font.delim`（分割＋延長片）で作る。
- 位置・間隔はセル（`U`）の整数倍。定数は `typeset.py` 冒頭の「組版定数（セル数）」にまとめる。

- 本家の作業開始時チェックに従い、まず `basis/docs/glyph_map.txt` で利用可能グリフを把握する。
- 収録字は本家が正。**本家に無い字は組版できない**ので、必要な字が欠けている場合は
  本家 [basis/docs/GLYPH_EXTENSION_PLAN.md] の作字計画へ起票する（こちらで作字しない）。
- 大型演算子（C2 15字）とギリシャアクセント（P7b 20字）は **本家では絵文字収録が凍結**
  されているが **OTF には収録される**ため、本リポジトリからは SVG として利用できる
  （本家 [basis/docs/GLYPH_EXTENSION_PLAN.md] §4Y）。
- 単位・型番合字（P2c）は本家で合成すら行わない凍結枠。必要なら本リポジトリ側で
  既存英字グリフを合成する（トークン名は本家の予約と衝突させないこと）。

---

[docs/TYPESET_SPEC.md]: docs/TYPESET_SPEC.md
[docs/HANDOFF_PLAN.md]: docs/HANDOFF_PLAN.md

## 技術スタック

本家に合わせる（`basis/requirements.txt` を土台にする）:

- **言語**: Python 3.11+
- **主要ライブラリ**: `fontTools`（メトリクス・カーニング・アウトライン）/ `cairosvg`（SVG→PNG）
  / `Pillow` / `numpy` `scipy`（SDF）/ `click`（CLI）/ `svgwrite`（合成 SVG 生成）
- **libcairo**: `cairosvg` が使う libcairo は pip では入らない。macOS（Homebrew）は `brew install cairo` ＋
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`（dyld の既定の探索先に無いため）。

---

## Python コーディング規則

本家と同一:

- スタイル: PEP 8 準拠
- 型ヒント: 全関数に付与（`from __future__ import annotations`）
- docstring: Google スタイル（日本語可）
- エラーハンドリング: フォント読み込み・SVG 変換は必要に応じて `try/except` でラップ

---

## コミットメッセージ規約

本家と同一: `<type>(<scope>): <subject>`
（type: `feat` `fix` `build` `docs` `chore` `style`）。
scope に `layout` `render` `api` `basis` `docs` を追加で用いてよい
（`basis` はサブモジュール参照コミットの更新）。

---

## 絶対に行わないこと

- `basis/` 内ファイルの変更・削除（変更は本家リポジトリで行う）
- **`basis/dist/` のデカール PNG を組版素材に使うこと**（「入力の契約」参照）
- PenchantManufacture 以外の商用フォント・第三者フォントのグリフパス流用
- 組版側でベースライン・縦バンドを動かすこと（フォント登録メトリクスをそのまま信頼する）
- ライセンス表記（CC BY 4.0 / 著作者名）の削除・改ざん
- 本家に本リポジトリ向けの分岐・依存を追加すること

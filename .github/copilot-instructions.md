# GitHub Copilot 向け補足 — PenchantManufacture_ImagePipeline

> **詳細指示の唯一の正（SSOT）は [../AGENTS.md](../AGENTS.md)。**
> 本ファイルは Copilot 向けの要点抜粋であり、齟齬がある場合は AGENTS.md を優先する。

## このリポジトリは何か

PenchantManufacture フォントのグリフから、**複数行にまたがる数式・技術表記を
1 枚の画像として組版する** Bot／アプリ向けパイプライン。
上流の `PenchantManufacture_ImageAssets` はサブモジュール **`basis/`**。

**著作権者**: RadianN_kswg / ラジアン（柏木主税） / **ライセンス**: CC BY 4.0

## 入力の契約（最重要）

- 使うのは **`basis/src/glyphs/` の SVG ＋ `basis/assets/fonts/PenchantManufacture.otf` の実メトリクス**。
- **`basis/dist/` のデカール PNG を組版素材にしない。** 1 字ごとに外ハロー 10px ＋
  キーライン 6px ＋ CROP_MARGIN 13px を持つため字間が二重になり、実メトリクスも覆い隠される。
- デカールの質感は**組版後の合成パスに** `basis/scripts/generate_decal.py` の SDF 実装を適用して与える。

## 先に読むもの

1. `basis/scripts/generate_roman.py` — 既に「GPOS カーニングを読んで合成 SVG を組み、
   デカール実装を共用する」実装がある。多段組版はこの拡張として書く。
2. `basis/AGENTS.md` — 字形契約・命名規則・ビルドフロー。
3. `basis/docs/GLYPH_EXTENSION_PLAN.md` §0 — 本家との責務分界。

## メトリクス

- upm 1000 / OS/2 win 帯 793・198（帯 991）を**全グリフ共通の縦バンド**として信頼する。
  組版側でベースラインを動かさない。
- 各 SVG 冒頭の `<!-- frame x=X0,X1 y=Y0,Y1 -->` が配置フレーム（横 = advance ∪ インク）。
- advance は 161 通り・111〜1036 units で**量子化されていない**。

## コーディング規則

Python 3.11+ / PEP 8 / 全関数に型ヒント（`from __future__ import annotations`）/
Google スタイル docstring（日本語可）。

## 絶対に行わないこと

- `basis/` 内ファイルの変更・削除
- `basis/dist/` のデカール PNG を組版素材に使うこと
- 第三者フォント・商用グリフのグリフパス流用
- ライセンス表記（CC BY 4.0 / 著作者名）の削除・改ざん
- 本家に本リポジトリ向けの分岐・依存を追加すること

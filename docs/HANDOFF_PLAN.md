# 引継ぎ資料（HANDOFF_PLAN）— 未対応タスクと本家連動

> 状態: v0.2（2026-09-10）。`basis/` 参照 `4b2b6ab`（PenchantManufacture **v4.0-release**）。
> **TeX 互換化のロードマップは [TEX_COMPAT_PLAN.md] へ分離した**（本書は本家連動と、
> TeX 互換に属さない未対応タスク・決定事項を扱う）。
> 本家（`basis/`）側の予定は `basis/docs/GLYPH_EXTENSION_PLAN.md` §6 を正とし、本書はそれに
> 対する**本リポジトリ側の対応**を記す。本家に下流向けの分岐・依存を入れないこと（[AGENTS.md]）。
>
> 著作権者: RadianN_kswg / ラジアン（柏木主税） / ライセンス: CC BY 4.0

---

## 0. 現在できること（実装 v0.1 = `scripts/typeset.py` 初版）

| 機能 | 状態 | 備考 |
| --- | --- | --- |
| 分数（入れ子可） | ✅ | バー = ステム幅 6 セル・数式軸 17 セル |
| 上付き／下付き | ✅ | 実グリフ置換 ＋ 50% 縮小代替（同帯配置） |
| 根号 | ✅ | 縦画を延長片で伸長 |
| 可変高括弧 `( ) [ ] { } \|` | ✅ | 垂直ステム区間で分割＋延長片。線幅不変 |
| 大型演算子の上下引数 `\limits` | ✅（記号は要指定） | `∑` 等は本家 OTF 待ち。当面は `Σ` `Π` |
| 行列 | ✅ | 列幅・列間・行間をセル量子化 |
| 複数行 `\\` | ✅ | 中央揃えのみ |
| 設計グリッド量子化・整数 px 出力 | ✅ | `--cell N` |
| クレジット埋め込み | ✅ | PNG tEXt / SVG `<desc>` |
| テスト | ✅ | `tests/test_typeset.py`（6 件） |
| **TeX 記法互換** | ⚠️ | LaTeX ソースは**そのままでは通らない**。環境・`\sum_{i=1}^{n}` 記法・関数名・数式スタイル・アクセントが未対応。計画は [TEX_COMPAT_PLAN.md] |

---

## 1. 本家（`basis/`）連動タスク

本家 [GLYPH_EXTENSION_PLAN.md] §6 の実装が進んだら、**参照コミットを更新**し以下を行う。

| # | 本家の予定 | 本家の相 | 本リポジトリでの対応 | 変更箇所 |
| --- | --- | --- | --- | --- |
| U1 | **C2 大型演算子 15 字**（∑ ∏ ∐ ∫ ∮ ∬ ∭ ∯ ⨁ ⨂ ⨀ ⋃ ⋂ ⋁ ⋀）を OTF に収録（絵文字収録は凍結） | §4 C2 / §4Y | `COMMANDS` に `\sum \prod \int` は登録済み → 収録されれば**無変更で動く**。残り 12 字のコマンド名を追加（`\coprod \oint \iint \iiint \oiint \bigoplus \bigotimes \bigodot \bigcup \bigcap \bigvee \bigwedge`）。`\sum` 単独時に自動で `\limits` 相当の上下配置にするか（`\sum_{i=1}^{n}` 記法）を決める | `typeset.py` `COMMANDS` / `layout("script")` |
| U2 | 大型演算子の字面は「正方枠いっぱい」で作字予定 | §4 C2 | 上下引数の `LIMIT_GAP`（4 セル）と `\limits` の中央揃え規則を実字形で再確認。`\int` は上下引数を右肩／右下に置く TeX 流儀（`\int_a^b`）も要検討 | `TYPESET_SPEC.md` §4.4 |
| U3 | **B2 矢印 15 字**（→ ← ↑ ↓ ↔ ↕ ⇒ ⇐ ⇔ ↦ ↳ ↰ ⤷ ⇌ ⇋） | P4a | `COMMANDS` に `\to \gets \uparrow \downarrow \leftrightarrow \Rightarrow \Leftarrow \Leftrightarrow \mapsto \rightleftharpoons \leftrightharpoons` 追加。`BINARY` に矢印を含め前後空きを付ける（`→` は登録済み） | `COMMANDS` / `BINARY` |
| U4 | **B3** ° ′ ″ ‴ | P4b | `\deg \prime` 追加。`′ ″` は上付き扱いにせず、実グリフの位置をそのまま使う | `COMMANDS` |
| U5 | **B9 既製分数** ½ ¼ ¾ ⅓ ⅔ ⅛ | P4c | 本リポジトリでは `\frac` で組めるため**対応不要**。1 行インライン用途で欲しければ文字として直接入力可 | — |
| U6 | **B10 製図記号** ⌀ ∠ ⊥ ∥ ⌒ ⌖ … | P4d | `\angle \perp \parallel` 追加。`⊥ ∥` は `BINARY` 相当の空き | `COMMANDS` / `BINARY` |
| U7 | **B1 残** ⊕ ⊗ ∘ | P4e | `\oplus \otimes \circ` 追加、`BINARY` へ | 同上 |
| U8 | **B8 山括弧** ⟨ ⟩ « » ‹ › | P4f | `\langle \rangle` を `\left \right` の対象に追加。`cuts()` が垂直ステム区間を見つけられない（山形は全域斜め）ため、**山括弧だけは延長片方式が使えない**。`(` と同様に扱えない場合は「伸長しない」か「上下端分割＋斜め延長」を要設計 | `Font.delim` |
| U9 | **P7b ギリシャアクセント 20 字**（OTF のみ） | §4Y | `COMMANDS` へ `\acute{α}` 相当は不要、文字直接入力で使える。対応表不要 | — |
| U10 | 下付き小文字（ᵢ ⱼ ₖ ₐ ₑ …）は本家に**予定なし** | — | 50% 縮小代替のまま（ステム 3 セル相当）。本家へ作字を依頼するなら U+1D62 ᵢ / U+2C7C ⱼ / U+2096 ₖ / U+2090 ₐ / U+2091 ₑ / U+2092 ₒ / U+2093 ₓ / U+1D65 ᵥ が数式頻出。収録されたら `SUB` 表に追記するだけで置換される | `SUB` |
| U11 | 本家がフォントを更新（v4.x）したとき | — | `U = 660/40`・`rule`・`axis`・上下付きの帯（28–48 / −12–8 セル）は**実測値**。`tests/test_typeset.py` が通るか確認し、`TYPESET_SPEC.md` §2 の表を再実測して更新。**v4.0-release（`4b2b6ab`）で実施済み（2026-09-10）**: 実測値に変化なし、テスト 6/6 通過、`docs/previews/` はバイト一致で再生成不要 | `TYPESET_SPEC.md` |

サブモジュール更新手順（[AGENTS.md]）:

```bash
git submodule update --remote basis
python tests/test_typeset.py && python scripts/build_previews.py
git add basis docs/previews && git commit -m "chore(basis): bump to <sha>"
```

---

## 2. 本リポジトリ単独の未対応タスク

優先度: **A**（Bot 運用に必要）> **B**（表現力）> **C**（仕上げ）。

> **TeX 互換に属するタスクは [TEX_COMPAT_PLAN.md] が正**。下表の T3・T4・T6・T7 は
> そちらの相へ吸収済みで、対応は次のとおり:
>
> | 本書 | TEX_COMPAT_PLAN の相 |
> | --- | --- |
> | T3（`&` 揃え） | X5（環境 `align` / `aligned`） |
> | T4（`\sum_{i=1}^{n}`） | X4（添字の TeX 化・`\limits` 後置化） |
> | T5（山括弧・斜め画の可変高） | X10（本家 P4f 待ち）＋フォールバックは本書のまま |
> | T6（行内の空きの再検討） | X2（アトム種別とスペーシング・§3 に設計値） |
> | T7（左揃え・右揃え） | X5（`cases` / `array` の列揃えと同じ実装） |
> | T9（`\text{…}` と空白） | X6（関数名・`\operatorname`）＋ X9（空白命令） |

| # | 優先 | 内容 | 設計メモ |
| --- | --- | --- | --- |
| T1 | A | **Bot／API 層**（参考: [X equal](https://misskey.io/@math_ba)。1 時間ごとに四則演算の問題画像を投稿） | `render()` → `to_png()` を呼ぶ薄い層のみ。問題生成・投稿は別モジュール。Misskey の Drive アップロード → ノート投稿（`drive/files/create` → `notes/create`）。**クレジット表記は Bot プロフィールか投稿本文に必須**（[AGENTS.md]「権限・ライセンス」） |
| T2 | A | **キャプション／背景**（「算数 小テスト（全1問）」のような見出し行、方眼背景） | 見出しは本フォントで組めばよい（`\\` 複数行 ＋ 左揃えオプション）。方眼は `to_svg` の `bg` を `<pattern>` に拡張。和文見出しが要るなら **PenchantManufacture-CJK** の責務（本家には作字しない） |
| T3 | B | **複数行の `&` 揃え**（`=` の位置を縦に揃える align 環境） | `vstack` に「`&` 直前までの幅」を集めて列幅を決める。行列と同じ `_split(…, "amp")` が流用できる |
| T4 | B | **`\sum_{i=1}^{n}` 記法**（`^` `_` を大型演算子に付けたら上下配置） | `layout("script")` で base が大型演算子（C2 集合）なら `\limits` へ振る。U1 と同時に |
| T5 | B | **山括弧・斜め画の可変高**（U8） | `cuts()` が空を返す字は現状 `ValueError`。「伸長しない」フォールバックを先に入れる |
| T6 | B | **行内の空きの再検討**（`OP_GAP` 11 セル、`THIN` 10 セル、関係子と二項演算子の区別） | TeX は relation（=）> binary（+）> ordinary の 3 段。今は一律 11 セル。実際の投稿画像で詰まりすぎ／空きすぎを見て決める |
| T7 | B | **左揃え・右揃えオプション**（複数行・行列列） | `vstack(align=)` は引数だけ用意済み（`"center"` 固定） |
| T8 | C | **デカール質感の適用**（本家 `generate_decal.py` の SDF・5 スキーム） | 本家の `load_mask(svg_path)` は高さ 512px 固定・`PAD` 前提。多段数式は縦長になるため、`render(mask, scheme, seed)` に**任意サイズのマスク**を渡す薄いラッパを本リポジトリ側に書く（本家は変更しない）。ハロー 10px / キーライン 6px は 512px 基準なので `--cell` と整合させる |
| T9 | C | **`\text{…}` と空白**（式中の語・単位表記 `5 kg`） | `\ ` で space の advance は入る。語は `\text{}` で `BINARY` 空き・カーニングを通常文字組みに切り替える |
| T10 | C | **エラー画像**（未収録字・構文エラー時に Bot が返す画像） | `ValueError` メッセージを本フォントで組んで返せば追加コード最小 |
| T11 | C | **SVG の `clipPath` id 衝突** | `_CLIP_ID` はプロセス内カウンタ。1 画像 1 SVG なら問題ないが、複数 SVG を 1 文書に埋め込む用途が出たら接頭辞を付ける |

---

## 3. 決定事項の記録（変更するなら理由を書く）

| 決定 | 理由 | 出所 |
| --- | --- | --- |
| 入力は OTF の実メトリクス＋アウトライン。`src/glyphs/*.svg` は読まない | 同じアウトラインを `SVGPathPen` で直接得られ、`generate_roman.py` と同じ経路になる。SVG を読むと frame コメントの解析が要る | [AGENTS.md]「入力の契約」 |
| 縦積みはインク境界（win 帯ではない） | win 帯（793/198）で積むと分子・分母の間に 130–200 units の空白が非対称に入る。TeX と同じくインクで積み、baseline は動かさない | TYPESET_SPEC §3 |
| 1 セル = 16.5 units、横はインク左端をセルに乗せる | 字面が 28×40 セル設計。sidebearing/advance は非整数セルなので、原点ではなくインクを揃える | TYPESET_SPEC §2 |
| 括弧・根号は分割＋延長片、等倍伸縮は禁止 | 伸縮すると 6 セルのステムが崩れる | 2026-09-08 作者指示 |
| 上付き／下付きの代替のみ 50% 縮小 | 収録済み上付き字が本体の 50%・28–48 セル帯で設計されているため、同寸・同位置に揃える | 同上 |
| 上引数＝下付き字、下引数＝上付き字 | 本家 `FUTURE_PLAN_20260827.md` §3-3 | 本家 docs/.private |
| 分数バー・上線の太さ = hyphen のステム幅 | 「フォントに無い図形は線幅を字形のステム幅に合わせて実測」 | [AGENTS.md]「メトリクスの読み方」 |
| `∑` と `Σ` は別字。`\sum` は C2 収録まで ValueError | 本家 SPEC の方針（Σ で代替しない） | `basis/docs/GLYPH_EXTENSION_PLAN.md` §4 C2 注 |

---

## 4. 作業開始時のチェック（本リポジトリ版）

1. `git submodule status` で `basis/` の参照コミットを確認し、`basis/docs/glyph_map.txt` で収録字を把握。
2. `python tests/test_typeset.py` が通ることを確認。
3. 組版規則を変えたら `docs/TYPESET_SPEC.md` を先に直し、`python scripts/build_previews.py` で
   `docs/previews/` を再生成して同じコミットに含める（本家の README プレビュー運用と同じ）。
4. TeX 互換に関わる作業なら [TEX_COMPAT_PLAN.md] §1 のフェーズ表で着手位置を確認し、
   §8 の「作者の判断が要る項目」が未決のフェーズには入らない。
5. コミット規約: `<type>(<scope>): <subject>`、scope は `layout` `render` `api` `basis` `docs`。

[AGENTS.md]: ../AGENTS.md
[GLYPH_EXTENSION_PLAN.md]: ../basis/docs/GLYPH_EXTENSION_PLAN.md
[TEX_COMPAT_PLAN.md]: TEX_COMPAT_PLAN.md

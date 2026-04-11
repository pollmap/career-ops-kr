# career-ops-kr (日本語)

> 韓国特化 AI 求職自動化エージェント — `santifer/career-ops` の思想を韓国の
> 金融/フィンテック/ブロックチェーン市場向けに移植したもの。User/System レイヤー分離により、
> 金融以外のドメインにもプリセット差し替えで展開可能。
>
> Luxon AI プロジェクト · Claude Code ベース · Python シングルスタック · v0.2.0

> **言語について**: このプロジェクトは韓国語ファーストです。モードプロンプト、レポート、
> CLI メッセージの大半は韓国語で記述されています。この README は国際読者のために韓国語版を
> 翻訳したものです。コードベース自体は 7 つのドメインプリセットで示されている通り
> 汎用化可能な設計で、韓国外でも新しいチャネル実装を追加することで使えます。

---

## なぜ作られたか — 創業者のコンテキスト

このツールは **Luxon AI 創業者 이찬희 (イ・チャンヒ)** が自身の求職ニーズから作りました。
忠北大学経営学部 3 年次休学中、資格取得 5 件を並行し、下半期のインターン応募を控える学生の状況:

- `dataq.or.kr`、`license.kofia.or.kr`、Linkareer など主要韓国サイトは
  **動的ロード + ログイン壁** で、LLM 単体ではスクレイピング不可能
- プログラムごとに「休学生可否 / 非専攻可否 / 卒業予定要件」がバラバラ → 資格判定が反復作業に
- 74 の対象プログラム × 9 のポータルを毎週手動ポーリングするのは非現実的
- 求職は **パイプライン化** しなければ生き残れない

個人の実需要で作られ、実戦で検証された後にオープンソース化されました。

---

## 主な特徴

- **16 個の Claude Code モード (v0.2)**
  - **Phase 1 (MVP)**: `scan` · `filter` · `score` · `pipeline` · `tracker` · `patterns` · `auto-pipeline`
  - **Phase 2**: `pdf` · `interview-prep` · `apply` · `followup` · `project` · `batch`
  - **Phase 3**: `training` · `deep` · `contacto`
  - **韓国ローカライゼーション**: `modes/kr/*`
- **9 + 9 チャネル** (MVP 9 + Sprint 3 スタブ 9)
  - MVP: Linkareer · Jobalio · Work24 청년 · 新韓投資証券 · Kiwoom KDA · KOFIA · DataQ · 韓国銀行 · Wanted
- **プラガブルなチャネルアーキテクチャ** — RSS/API/requests → Scrapling → Playwright の優先順
- **Scrapling 統合レイヤー** (Sprint 2) — adaptive scraping
- **7 つのドメインプリセット**: `finance` · `dev` · `design` · `marketing` · `research` · `public` · `edu`
- **User / System レイヤー分離** — システム更新時にユーザー設定ファイルを保護
- **HITL 5 ゲート** — 自動応募は永久禁止、重要判断は全て人間確認
- **Obsidian Vault + SQLite 二重ストレージ**
- **Discord プッシュ通知** — HERMES bot 経由で `#luxon-jobs` チャンネル
- **MCP サーバーラッパー** — 10 ツールを Nexus MCP に編入可能
- **Textual TUI ダッシュボード** — ターミナル上でパイプライン可視化
- **LLM 二次スコアラー** — D~B 中間グレードの曖昧さを解消

---

## ドメイン対応 / Generalization

career-ops-kr は元々 **韓国金融ドメイン** 向けですが、`CLAUDE.md` が強制する
**User/System レイヤー分離** のおかげで、エンジン (`career_ops_kr/`) はそのまま、
プリセットだけ差し替えて金融外のドメインに展開できます。

| preset_id | ドメイン | 代表ポータル | 主な archetype |
|-----------|----------|--------------|----------------|
| `finance` | 金融/フィンテック/ブロックチェーン (既定) | Linkareer·Jobalio·DataQ·韓国銀行·KOFIA | ブロックチェーン·金融IT·リサーチ·フィンテック |
| `dev` | ソフトウェアエンジニア | Wanted·Programmers·Jumpit·JobKorea·Rocketpunch | バックエンド·フロントエンド·DevOps·ML |
| `design` | UX/UI·プロダクト | Wanted·Designerss·Notefolio | UX·UI·プロダクト·ビジュアル |
| `marketing` | デジタルマーケ·グロース | Wanted·Superookie·Saramin | パフォーマンス·コンテンツ·ブランド·グロース |
| `research` | リサーチ·データ分析 | 韓国銀行·KDI·DataQ·KOSSDA | 経済·政策·データサイエンス |
| `public` | 公共/政府/青年政策 | Jobalio·Narailteo·Work24 | 公共機関·省庁·公企業 |
| `edu` | 教育·EdTech·研究助手 | 学校公告·Eduwill·Wanted | 研究助手·チューター·EdTech |

> 韓国金融用語対照: **휴학생** = 休学生 / **비전공자** = 非専攻者 / **자격증** = 資格証 /
> **공고** = 公告(公募) / **공모전** = コンペティション / **인턴** = インターン

---

## インストール

```bash
git clone https://github.com/pollmap/career-ops-kr.git
cd career-ops-kr
uv sync
uv run playwright install chromium
uv run career-ops --help
```

---

## 使い方

```bash
# プリセット一覧
career-ops init --list-presets

# ドメイン選択で初期化
career-ops init --preset dev
career-ops init --preset research
career-ops init --preset finance  # 既定値

# 毎日のスキャン (MVP フロー)
career-ops scan
career-ops filter
career-ops pipeline

# Phase 2 モード
career-ops interview-prep
career-ops pdf
career-ops followup

# MCP サーバー (Nexus MCP 編入用)
python -m career_ops_kr.mcp_server

# TUI ダッシュボード
career-ops ui
```

---

## 配布モデル

- **本人利用**: 作者の Windows 11 ローカル (finance プリセット)
- **チーム**: Luxon AI メンバーが git clone して `--preset <各自のドメイン>`
- **オープンソース**: `presets/*.yml` の PR ベース貢献

---

## 参考

- [santifer/career-ops](https://github.com/santifer/career-ops) — 原典の思想
- [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) — チャネルパターン
- `CLAUDE.md` — エージェント作業ルール (User/System 分離、HITL ゲート)
- `CONTRIBUTING.md` — 貢献ガイド
- `CHANGELOG.md` — バージョン履歴

## ライセンス

MIT © 2026 이찬희 (Luxon AI)

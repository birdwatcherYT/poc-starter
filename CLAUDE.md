# CLAUDE.md

このリポで作業する Claude / 共同作業者向けのルール。リポ構造・基本操作・ワークフローは README と `make help` を見ること。

## コードを書くときのルール

- `from __future__ import annotations` を書かない（Python 3.12 前提、PEP 604 が標準で使える）
- docstring・コメントは不自然な位置で改行しない。文として自然な切れ目でのみ改行
- コメント・docstring は WHAT ではなく WHY を書く
- 同一パッケージ内の依存は相対 import、外部パッケージ（`schema`, `sqlalchemy` 等）は絶対 import
- import はファイル冒頭にまとめる。関数内・条件分岐内の遅延 import は書かない
- try-except は外部境界で例外を別の形に変換する時、握りつぶしても問題ない時、後始末が必要な時だけ書く
- 「ログを出して raise」するだけの try-except は書かない。FastAPI / uvicorn が自動で traceback を出すので二重ログになって本当の原因が埋もれる
- Python を変更したら該当サブプロジェクトの fmt を実行（`make -C api fmt` / `make -C database fmt`）、Terraform を変更したら `make -C infra fmt`

## ドキュメントの方針

- **README**: そのコンポーネントの責務、構成、基本操作（run / test / build / fmt 等）、概念的な「考え方」を書く。利用者が最初に開く前提
- **Makefile のターゲットのコメント**: 各コマンドの説明。`make help` で読める
- **CLAUDE.md**: Claude / 共同作業者向けのルール、構造判断のガードレール、README に書きにくい流儀
- 同じ情報を3箇所に書かない。コマンドの詳細は Makefile のコメントが一次情報、README には主要なものだけ抜粋する

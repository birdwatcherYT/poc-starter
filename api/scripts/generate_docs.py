"""FastAPI の app.openapi() をリポジトリルートの docs/openapi.json と docs/index.html に書き出す。

出力先をルート docs/ にしているのは GitHub Pages のデフォルトソース（main ブランチ /docs）と揃えるため。
HTML は Redocly CLI を npx 経由で呼ぶので、Node.js / npx がインストールされている必要がある。
npx が見つからない場合は JSON のみ生成して終了する（CI でも安全に動く）。
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = API_DIR.parent
sys.path.insert(0, str(API_DIR))

# api.py の lifespan 検証で起動失敗しないよう、必須 DB 環境変数のスタブを入れる。
# スキーマ生成中は lifespan に入らない（TestClient 等を使わない）ので接続は走らない。
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "openapi_stub")
os.environ.setdefault("DB_USER", "openapi_stub")

from api import app

DOCS_DIR = REPO_ROOT / "docs"
OPENAPI_JSON = DOCS_DIR / "openapi.json"
INDEX_HTML = DOCS_DIR / "index.html"


def generate_openapi_json() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    with OPENAPI_JSON.open("w") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)
    print(f"Generated {OPENAPI_JSON}")


def generate_html() -> None:
    if shutil.which("npx") is None:
        print(
            "npx が見つからないため HTML 生成をスキップ（Node.js を入れると有効化される）"
        )
        return
    cmd = [
        "npx",
        "--yes",
        "@redocly/cli",
        "build-docs",
        str(OPENAPI_JSON),
        "--output",
        str(INDEX_HTML),
    ]
    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print(f"Generated {INDEX_HTML}")


if __name__ == "__main__":
    generate_openapi_json()
    generate_html()

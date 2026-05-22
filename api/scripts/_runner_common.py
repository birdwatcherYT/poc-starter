"""runner スクリプト共通の HTTP クライアントとリクエスト/レスポンス表示ヘルパー。

- BASE_URL が http:// で始まる場合: 認証ヘッダなし（ローカル開発向け）
- BASE_URL が https:// で始まる場合: IAP 通過用に gcloud identity token を自動取得して付与
"""

import argparse
import json
import os
import subprocess
from typing import Any

import httpx


def _gcloud_id_token() -> str:
    proc = subprocess.run(
        ["gcloud", "auth", "print-identity-token"],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def make_client(default_url: str = "http://localhost:8080") -> httpx.Client:
    """`BASE_URL` 環境変数 / `--url` 引数で接続先を切り替えられる httpx.Client を返す。"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--url", default=os.getenv("BASE_URL", default_url))
    args, _ = parser.parse_known_args()
    base_url = args.url

    headers: dict[str, str] = {}
    if base_url.startswith("https://"):
        headers["Authorization"] = f"Bearer {_gcloud_id_token()}"

    return httpx.Client(base_url=base_url, headers=headers, timeout=10.0)


def _dump(label: str, body: object) -> None:
    print(f"--- {label} ---")
    print(json.dumps(body, indent=2, ensure_ascii=False, default=str))


def call(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json_body: Any = None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    """`method path` を叩き、request / status / response を整形表示する。

    4xx / 5xx でも response を表示してから raise_for_status() で例外を上げる。
    """
    print(f"{method} {client.base_url}{path}")
    if json_body is not None:
        _dump("request", json_body)
    if params:
        _dump("query", params)

    res = client.request(method, path, json=json_body, params=params)
    print(f"\nstatus: {res.status_code}")
    try:
        _dump("response", res.json())
    except ValueError:
        print(res.text)
    res.raise_for_status()
    return res

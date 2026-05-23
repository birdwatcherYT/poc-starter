"""POST /documents で 2 件保存し、GET /documents/similar で類似検索する動作確認。"""

from _runner_common import call, make_client


def main() -> None:
    with make_client() as client:
        call(
            client,
            "POST",
            "/documents",
            json_body={"title": "犬", "content": "犬は忠実な動物だ。"},
        )
        call(
            client,
            "POST",
            "/documents",
            json_body={"title": "猫", "content": "猫は気まぐれな動物だ。"},
        )
        call(client, "GET", "/documents/similar?q=ペット&limit=5")


if __name__ == "__main__":
    main()

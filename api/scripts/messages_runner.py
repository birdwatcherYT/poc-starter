"""POST /messages → GET /messages を順に叩いて request / response を表示する。"""

from _runner_common import call, make_client


def main() -> None:
    payload = {"message": "hello from runner", "author": "messages_runner"}
    with make_client() as client:
        call(client, "POST", "/messages", json_body=payload)
        call(client, "GET", "/messages?limit=5")


if __name__ == "__main__":
    main()

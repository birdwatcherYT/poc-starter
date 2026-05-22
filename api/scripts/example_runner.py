"""/example/echo にメッセージを送って request / response を表示する。"""

from _runner_common import call, make_client


def main() -> None:
    payload = {"message": "hello from runner", "author": "example_runner"}
    with make_client() as client:
        call(client, "POST", "/example/echo", json_body=payload)


if __name__ == "__main__":
    main()

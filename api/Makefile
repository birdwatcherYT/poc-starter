.DEFAULT_GOAL := help

# .env があれば取り込んで Make 変数 & サブプロセス env として参照可能にする。
# 行頭 export で sh コマンドからも見える。CLI で渡した値は include より優先される。
-include .env
export

# --- デプロイ用変数 ---
# コマンドラインまたは環境変数（.env を含む）で上書き可。
PROJECT_ID    ?= $(GOOGLE_CLOUD_PROJECT)
REGION        ?= asia-northeast1
SERVICE_NAME  ?= poc-starter-api
AR_REPO       ?= poc-starter
IMAGE_TAG     ?= latest
IMAGE_URL     := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(AR_REPO)/api:$(IMAGE_TAG)
BUILD_SA      ?= cloud-build-sa@$(PROJECT_ID).iam.gserviceaccount.com

help: ## ヘルプを表示
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

run-docker: ## docker compose で api 起動（src / schema は bind mount）
	docker compose -f ../docker-compose.yml up api

run: ## uvicorn --reload で :8080 起動
	uv run uvicorn api:app --reload --port 8080

fmt: ## ruff format と ruff check --fix
	uv run ruff format .
	uv run ruff check --fix .

fmt-unsafe: ## ruff format と ruff check --fix --unsafe-fixes
	uv run ruff format .
	uv run ruff check --fix --unsafe-fixes .

lint: ## ruff format --check と ruff check
	uv run ruff format --check .
	uv run ruff check .

test: ## pytest（Testcontainers で PG を立てる。gcloud 認証切れの docker credential helper を踏まないよう空の DOCKER_CONFIG を使う）
	@mkdir -p /tmp/poc-starter-empty-docker-config && echo '{}' > /tmp/poc-starter-empty-docker-config/config.json
	DOCKER_CONFIG=/tmp/poc-starter-empty-docker-config uv run pytest -v

docs: ## docs/openapi.json と docs/index.html (Redocly HTML) を生成
	uv run scripts/generate_docs.py

docker-build: ## compose 用 api イメージをビルド（Dockerfile / lock / 依存変更後）
	docker compose -f ../docker-compose.yml build api

require-project:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID が必要です（GOOGLE_CLOUD_PROJECT を設定するか PROJECT_ID=... で渡してください）" && exit 1)

# build context はリポ root（api/Dockerfile が database/ を参照するため）。
# --config は cwd 基準で解決されるので、api/ から相対指定すると api/api/... になって失敗する。
BUILD_SUBMIT = gcloud builds submit $(CURDIR)/.. \
	--project=$(PROJECT_ID) \
	--region=$(REGION) \
	--config=$(CURDIR)/cloudbuild.yaml \
	--service-account=projects/$(PROJECT_ID)/serviceAccounts/$(BUILD_SA) \
	--default-buckets-behavior=regional-user-owned-bucket \
	--substitutions=_REGION=$(REGION),_AR_REPO=$(AR_REPO),_TAG=$(IMAGE_TAG)

build: require-project ## 非同期で Cloud Build にビルドを投げて即終了（バックグラウンドで進む）
	$(BUILD_SUBMIT) --async

build-sync: require-project ## 同期ビルド（完了を待つ）
	$(BUILD_SUBMIT)

deploy: require-project ## 現在の IMAGE_TAG で Cloud Run サービスを更新（ビルドはしない）
	gcloud run services update $(SERVICE_NAME) \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--image=$(IMAGE_URL)

build-deploy: build-sync deploy ## 同期ビルド後に deploy

.PHONY: help run run-docker fmt fmt-unsafe lint test docs docker-build require-project build build-sync deploy build-deploy

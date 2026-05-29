.DEFAULT_GOAL := help

-include .env
export

# Alembic は database 自身の pyproject.toml で管理。uv の自動同期で venv が作られる。
ALEMBIC := uv run alembic

# --- デプロイ用変数（api/Makefile と揃える） ---
PROJECT_ID ?= $(GOOGLE_CLOUD_PROJECT)
REGION     ?= asia-northeast1
AR_REPO    ?= poc-starter
IMAGE_TAG  ?= latest
IMAGE_URL  := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(AR_REPO)/migrate:$(IMAGE_TAG)
BUILD_SA   ?= cloud-build-sa@$(PROJECT_ID).iam.gserviceaccount.com

# ローカル開発用デフォルト（docker-compose.yml の defaults と一致させること）。
# 環境変数で上書き可能。本番に流す場合は DB_URL を直接指定する。
DB_HOST     ?= localhost
DB_PORT     ?= 5432
DB_NAME     ?= poc
DB_USER     ?= app_user
DB_PASSWORD ?= app_password

# env.py 側で DB_HOST/DB_PORT/... から URL を組むので、ここでは DB_URL は組まない。
# DB_URL を明示的に渡したい場合（リモート接続など）はシェル env で上書きすれば
# env.py が優先採用する。
export DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD

help: ## ヘルプを表示
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'

fmt: ## ruff format と ruff check --fix
	uv run ruff format .
	uv run ruff check --fix .

lint: ## ruff format --check と ruff check
	uv run ruff format --check .
	uv run ruff check .

gen-migrate: ## 新しい migration を作成（NAME=xxx、デフォルトはモデル差分から自動生成、EMPTY=1 で空雛形）
	@test -n "$(NAME)" || (echo "使い方: make gen-migrate NAME=<name> [EMPTY=1]" && exit 1)
	$(ALEMBIC) -c $(CURDIR)/alembic.ini revision $(if $(EMPTY),,--autogenerate) -m "$(NAME)"

migrate-up: ## ローカル DB に全マイグレーションを適用
	$(ALEMBIC) -c $(CURDIR)/alembic.ini upgrade head

migrate-down: ## ローカル DB のマイグレーションを 1 ステップ戻す
	$(ALEMBIC) -c $(CURDIR)/alembic.ini downgrade -1

migrate-down-all: ## ローカル DB を全 migration 分 down する（リモート DB は拒否）
	@case "$(DB_HOST)" in \
	  localhost|127.0.0.1|host.docker.internal) ;; \
	  *) echo "ローカル DB 以外には実行を拒否します（DB_HOST=$(DB_HOST)）"; exit 1 ;; \
	 esac
	$(ALEMBIC) -c $(CURDIR)/alembic.ini downgrade base

migrate-status: ## 現在の DB に適用済みのリビジョンを表示
	$(ALEMBIC) -c $(CURDIR)/alembic.ini current

migrate-history: ## migration の履歴を表示
	$(ALEMBIC) -c $(CURDIR)/alembic.ini history

migrate-check: ## schema/models/ と DB に差分が無いか確認（差分があれば exit 1）
	$(ALEMBIC) -c $(CURDIR)/alembic.ini check

# --- Cloud SQL 操作（cloudsql-*） ---
# proxy 経由: 別ターミナルで cloudsql-proxy を起動してから cloudsql-psql / cloudsql-migrate / cloudsql-grant。
# Job 経由: cloudsql-migrate-job（cloud-sql-proxy 不要）。
# ※ 値の取得は terraform / gcloud にネットワーク I/O を伴うため、`$(shell ...)` を
#    トップレベルに書くと `make` を打つたびに数秒の待ちが発生する。
#    そのため各 recipe 内で必要なときだけ shell で評価する。
ENV ?= dev
TF_DIR_REL := ../infra/terraform/env/$(ENV)

require-cloud-project:
	@test -n "$(PROJECT_ID)" || { echo "GOOGLE_CLOUD_PROJECT が未設定です。.env を作成するか PROJECT_ID=... を指定してください" >&2; exit 1; }

set-quota-project: require-cloud-project ## ADC の quota project を PROJECT_ID に揃える（gcloud で 403 が出るとき用）
	@echo "ADC quota project を $(PROJECT_ID) に設定"
	gcloud auth application-default set-quota-project "$(PROJECT_ID)"

cloudsql-proxy: ## cloud-sql-proxy を :5432 で起動（INSTANCE_CONNECTION_NAME 自動取得、ENV=dev|prod）
	@CONN=$$(terraform -chdir=$(TF_DIR_REL) output -raw instance_connection_name 2>/dev/null); \
	 test -n "$$CONN" || { echo "INSTANCE_CONNECTION_NAME が取得できません。terraform apply 済みか確認してください" >&2; exit 1; }; \
	 echo "cloud-sql-proxy $$CONN --port 5432"; \
	 exec cloud-sql-proxy $$CONN --port 5432

cloudsql-psql: require-cloud-project ## cloud-sql-proxy 経由で Cloud SQL に psql 接続（別ターミナルで cloudsql-proxy 起動が必要）
	@DB_NAME_VAL="$(DB_NAME)"; \
	 DB_USER_VAL=$$(terraform -chdir=$(TF_DIR_REL) output -raw app_user 2>/dev/null || echo "app_user"); \
	 if [ -z "$$DB_NAME_VAL" ]; then \
	   DB_NAME_VAL=$$(terraform -chdir=$(TF_DIR_REL) output -raw db_name 2>/dev/null || echo "poc"); \
	 fi; \
	 SECRET=$$(terraform -chdir=$(TF_DIR_REL) output -raw app_user_password_secret_id 2>/dev/null || echo "poc-starter-db-app-user-password"); \
	 PW=$$(gcloud secrets versions access latest --project=$(PROJECT_ID) --secret=$$SECRET 2>/dev/null | python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.read(),safe=""))'); \
	 test -n "$$PW" || { echo "app_user パスワードが取得できません（project=$(PROJECT_ID) secret=$$SECRET）" >&2; exit 1; }; \
	 echo "接続: $$DB_USER_VAL@localhost:5432/$$DB_NAME_VAL（cloud-sql-proxy が :5432 で待機していること）"; \
	 exec psql "postgres://$$DB_USER_VAL:$$PW@localhost:5432/$$DB_NAME_VAL?sslmode=disable"

cloudsql-migrate: require-cloud-project ## cloud-sql-proxy 経由でリモート DB にマイグレーション適用（ENV=dev|prod）
	@SECRET=$$(terraform -chdir=$(TF_DIR_REL) output -raw app_user_password_secret_id 2>/dev/null || echo "poc-starter-db-app-user-password"); \
	 PW=$$(gcloud secrets versions access latest --project=$(PROJECT_ID) --secret=$$SECRET 2>/dev/null); \
	 test -n "$$PW" || { echo "app_user パスワードが Secret Manager から取得できません（project=$(PROJECT_ID) secret=$$SECRET）" >&2; exit 1; }; \
	 DB_HOST=localhost DB_PORT=5432 DB_NAME=$(DB_NAME) DB_USER=app_user DB_PASSWORD="$$PW" \
	   $(ALEMBIC) -c $(CURDIR)/alembic.ini upgrade head

cloudsql-grant: require-cloud-project ## cloud-sql-proxy 経由で seed/grants.sql を実行（terraform 設定から自動取得）
	@TFVARS=$(TF_DIR_REL)/terraform.tfvars; \
	 APP_USER_VAL="$(APP_USER)"; \
	 DEV_GROUP_VAL="$(DEV_GROUP)"; \
	 DB_NAME_VAL="$(DB_NAME)"; \
	 if [ -z "$$APP_USER_VAL" ]; then APP_USER_VAL=$$(terraform -chdir=$(TF_DIR_REL) output -raw app_user 2>/dev/null || echo "app_user"); fi; \
	 if [ -z "$$DB_NAME_VAL" ]; then DB_NAME_VAL=$$(terraform -chdir=$(TF_DIR_REL) output -raw db_name 2>/dev/null || echo "poc"); fi; \
	 if [ -z "$$DEV_GROUP_VAL" ] && [ -f $$TFVARS ]; then \
	   DEV_GROUP_VAL=$$(awk -F '=' '/^developer_group/ {gsub(/[" ]/, "", $$2); print $$2}' $$TFVARS); \
	 fi; \
	 test -n "$$DEV_GROUP_VAL" \
	   || { echo "DEV_GROUP を解決できません（tfvars の developer_group か DEV_GROUP=... を指定してください）" >&2; exit 1; }; \
	 SECRET=$$(terraform -chdir=$(TF_DIR_REL) output -raw app_user_password_secret_id 2>/dev/null || echo "poc-starter-db-app-user-password"); \
	 PW=$$(gcloud secrets versions access latest --project=$(PROJECT_ID) --secret=$$SECRET 2>/dev/null | python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.read(),safe=""))'); \
	 test -n "$$PW" || { echo "app_user パスワードが取得できません（project=$(PROJECT_ID) secret=$$SECRET）" >&2; exit 1; }; \
	 echo "APP_USER=$$APP_USER_VAL DEV_GROUP=$$DEV_GROUP_VAL DB_NAME=$$DB_NAME_VAL"; \
	 psql "postgres://app_user:$$PW@localhost:5432/$$DB_NAME_VAL?sslmode=disable" \
	   -v app_user=$$APP_USER_VAL \
	   -v dev_group=$$DEV_GROUP_VAL \
	   -v db_name=$$DB_NAME_VAL \
	   -f seed/grants.sql

cloudsql-migrate-job: require-cloud-project ## Cloud Run Job 経由で migrate を実行（cloud-sql-proxy 不要）
	@JOB=$$(terraform -chdir=$(TF_DIR_REL) output -raw migrate_job_name 2>/dev/null); \
	 REGION=$$(terraform -chdir=$(TF_DIR_REL) output -raw region 2>/dev/null || echo "asia-northeast1"); \
	 test -n "$$JOB" || { echo "migrate_job_name が取得できません。terraform apply 済みか確認してください" >&2; exit 1; }; \
	 gcloud run jobs execute $$JOB --region=$$REGION --project=$(PROJECT_ID) --wait

cloudsql-reset: require-cloud-project ## cloud-sql-proxy 経由でリモート DB を初期化（public スキーマごと作り直し→migrate→grant）。データ全消去、FORCE=1 で確認省略
	@DB_NAME_VAL="$(DB_NAME)"; \
	 if [ -z "$$DB_NAME_VAL" ]; then DB_NAME_VAL=$$(terraform -chdir=$(TF_DIR_REL) output -raw db_name 2>/dev/null || echo "poc"); fi; \
	 if [ -z "$(FORCE)" ]; then \
	   printf "リモート DB '%s'（project=%s）の public スキーマを破棄し全データを消去します。続行するには 'yes' と入力: " "$$DB_NAME_VAL" "$(PROJECT_ID)"; \
	   read ans; [ "$$ans" = "yes" ] || { echo "中止しました"; exit 1; }; \
	 fi; \
	 SECRET=$$(terraform -chdir=$(TF_DIR_REL) output -raw app_user_password_secret_id 2>/dev/null || echo "poc-starter-db-app-user-password"); \
	 PW=$$(gcloud secrets versions access latest --project=$(PROJECT_ID) --secret=$$SECRET 2>/dev/null | python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.read(),safe=""))'); \
	 test -n "$$PW" || { echo "app_user パスワードが取得できません（project=$(PROJECT_ID) secret=$$SECRET）" >&2; exit 1; }; \
	 printf "public スキーマを作り直します（DB=%s）\n" "$$DB_NAME_VAL"; \
	 psql "postgres://app_user:$$PW@localhost:5432/$$DB_NAME_VAL?sslmode=disable" \
	   -v ON_ERROR_STOP=1 \
	   -c "DROP SCHEMA public CASCADE" \
	   -c "CREATE SCHEMA public"
	$(MAKE) cloudsql-migrate
	$(MAKE) cloudsql-grant

COMPOSE := docker compose -f ../docker-compose.yml

db-up: ## ローカル postgres を起動して migration を適用
	$(COMPOSE) up -d --wait postgres
	$(MAKE) migrate-up

db-down: ## ローカル postgres を停止（ボリュームは残す）
	$(COMPOSE) down

db-del: ## ローカル postgres とボリュームを削除
	$(COMPOSE) down -v

psql: ## docker compose のローカル postgres に psql で接続
	$(COMPOSE) exec postgres psql -U $(DB_USER) -d $(DB_NAME)

require-project:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID が必要です（GOOGLE_CLOUD_PROJECT を設定するか PROJECT_ID=... で渡してください）" && exit 1)

BUILD_SUBMIT = gcloud builds submit . \
	--project=$(PROJECT_ID) \
	--region=$(REGION) \
	--config=cloudbuild.yaml \
	--service-account=projects/$(PROJECT_ID)/serviceAccounts/$(BUILD_SA) \
	--default-buckets-behavior=regional-user-owned-bucket \
	--substitutions=_REGION=$(REGION),_AR_REPO=$(AR_REPO),_TAG=$(IMAGE_TAG)

build: require-project ## 非同期で Cloud Build に migrate イメージをビルド
	$(BUILD_SUBMIT) --async

build-sync: require-project ## 同期ビルド（完了まで待つ）
	$(BUILD_SUBMIT)

deploy: require-project ## 現在の IMAGE_TAG で migrate-job の image を更新（ビルドはしない）
	@JOB=$$(terraform -chdir=$(TF_DIR_REL) output -raw migrate_job_name 2>/dev/null); \
	 test -n "$$JOB" || { echo "migrate_job_name が取得できません。terraform apply 済みか確認してください" >&2; exit 1; }; \
	 gcloud run jobs update $$JOB \
	   --project=$(PROJECT_ID) \
	   --region=$(REGION) \
	   --image=$(IMAGE_URL)

build-deploy: build-sync deploy ## 同期ビルド → migrate-job の image を更新

.PHONY: help fmt lint gen-migrate migrate-up migrate-down migrate-down-all migrate-status migrate-history migrate-check cloudsql-proxy cloudsql-psql cloudsql-migrate cloudsql-grant cloudsql-migrate-job cloudsql-reset set-quota-project db-up db-down db-del psql require-project require-cloud-project build build-sync deploy build-deploy

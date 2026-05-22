.DEFAULT_GOAL := help

# 共有設定は api/.env から取り込む（GOOGLE_CLOUD_PROJECT / DB_* など）。
# 存在しなくてもエラーにしないため -include を使う。
-include ../api/.env
export

MIGRATE_IMAGE := migrate/migrate:v4.17.0

# --- デプロイ用変数（api/Makefile と揃える） ---
PROJECT_ID ?= $(GOOGLE_CLOUD_PROJECT)
REGION     ?= asia-northeast1
AR_REPO    ?= poc-starter
IMAGE_TAG  ?= latest
IMAGE_URL  := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(AR_REPO)/migrate:$(IMAGE_TAG)
BUILD_SA   ?= cloud-build-sa@$(PROJECT_ID).iam.gserviceaccount.com

# ローカル開発用デフォルト（docker-compose.yml の defaults と一致させること）。
# 環境変数で上書き可能。本番に流す場合は DB_URL を直接指定する。
DB_HOST     ?= host.docker.internal
DB_PORT     ?= 5432
DB_NAME     ?= poc
DB_USER     ?= app_user
DB_PASSWORD ?= app_password

DB_URL ?= postgres://$(DB_USER):$(DB_PASSWORD)@$(DB_HOST):$(DB_PORT)/$(DB_NAME)?sslmode=disable

help: ## ヘルプを表示
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

gen-migrate: ## up/down マイグレーションファイルを作成（NAME=xxx）
	@test -n "$(NAME)" || (echo "使い方: make gen-migrate NAME=<name>" && exit 1)
	@TS=$$(date +%s); \
	 touch migrations/$${TS}_$(NAME).up.sql \
	       migrations/$${TS}_$(NAME).down.sql; \
	 echo "Created migrations/$${TS}_$(NAME).{up,down}.sql"

migrate-up: ## ローカル DB に全マイグレーションを適用
	docker run --rm --network host \
	  -v $(CURDIR)/migrations:/migrations \
	  $(MIGRATE_IMAGE) -path=/migrations -database="$(DB_URL)" up

migrate-down: ## ローカル DB のマイグレーションを 1 ステップ戻す
	docker run --rm --network host \
	  -v $(CURDIR)/migrations:/migrations \
	  $(MIGRATE_IMAGE) -path=/migrations -database="$(DB_URL)" down 1

migrate-down-all: ## ローカル DB を全 migration 分 down する（リモート DB は拒否）
	@echo "$(DB_URL)" | grep -qE "host\.docker\.internal|localhost|127\.0\.0\.1" \
	  || (echo "ローカル DB 以外には実行を拒否します（DB_URL=$(DB_URL)）" && exit 1)
	docker run --rm --network host \
	  -v $(CURDIR)/migrations:/migrations \
	  $(MIGRATE_IMAGE) -path=/migrations -database="$(DB_URL)" down -all

# --- リモート Cloud SQL 操作（cloud-sql-proxy 経由） ---
# ※ 値の取得は terraform / gcloud にネットワーク I/O を伴うため、`$(shell ...)` を
#    トップレベルに書くと `make` を打つたびに数秒の待ちが発生する。
#    そのため各 recipe 内で必要なときだけ shell で評価する。
# ※ PROJECT_ID は api/.env の GOOGLE_CLOUD_PROJECT を真実のソースとし、gcloud には
#    常に --project で渡す。gcloud config のアクティブプロジェクトに依存しないため、
#    複数 GCP プロジェクトを横断しても誤ったプロジェクトを叩く事故を防げる。
ENV ?= dev
TF_DIR_REL := ../infra/terraform/env/$(ENV)

require-cloud-project:
	@test -n "$(PROJECT_ID)" || { echo "GOOGLE_CLOUD_PROJECT が未設定です。先に make -C infra set-project PROJECT_ID=<id> を実行してください" >&2; exit 1; }

set-quota-project: require-cloud-project ## ADC の quota project を PROJECT_ID に揃える（gcloud で 403 が出るとき用）
	@echo "ADC quota project を $(PROJECT_ID) に設定"
	gcloud auth application-default set-quota-project "$(PROJECT_ID)"

cloudsql-proxy: ## cloud-sql-proxy を :5432 で起動（INSTANCE_CONNECTION_NAME 自動取得、ENV=dev|prod）
	@CONN=$$(terraform -chdir=$(TF_DIR_REL) output -raw instance_connection_name 2>/dev/null); \
	 test -n "$$CONN" || { echo "INSTANCE_CONNECTION_NAME が取得できません。terraform apply 済みか確認してください" >&2; exit 1; }; \
	 echo "cloud-sql-proxy $$CONN --port 5432"; \
	 exec cloud-sql-proxy $$CONN --port 5432

migrate-cloudsql: require-cloud-project ## cloud-sql-proxy 経由でリモート DB にマイグレーション適用（ENV=dev|prod）
	@SECRET=$$(terraform -chdir=$(TF_DIR_REL) output -raw app_user_password_secret_id 2>/dev/null || echo "poc-starter-db-app-user-password"); \
	 PW=$$(gcloud secrets versions access latest --project=$(PROJECT_ID) --secret=$$SECRET 2>/dev/null | python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.read(),safe=""))'); \
	 test -n "$$PW" || { echo "app_user パスワードが Secret Manager から取得できません（project=$(PROJECT_ID) secret=$$SECRET）" >&2; exit 1; }; \
	 docker run --rm \
	   -v $(CURDIR)/migrations:/migrations \
	   $(MIGRATE_IMAGE) -path=/migrations \
	   -database="postgres://app_user:$$PW@host.docker.internal:5432/$(DB_NAME)?sslmode=disable" up

run-migrate-job: require-cloud-project ## 本番フロー: terraform で作られた migrate-job (Cloud Run Job) を実行
	@JOB=$$(terraform -chdir=$(TF_DIR_REL) output -raw migrate_job_name 2>/dev/null); \
	 REGION=$$(terraform -chdir=$(TF_DIR_REL) output -raw region 2>/dev/null || echo "asia-northeast1"); \
	 test -n "$$JOB" || { echo "migrate_job_name が取得できません。terraform apply 済みか確認してください" >&2; exit 1; }; \
	 gcloud run jobs execute $$JOB --region=$$REGION --project=$(PROJECT_ID) --wait

grant-cloudsql: require-cloud-project ## cloud-sql-proxy 経由で seed/grants.sql を実行（terraform 設定から自動取得）
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

.PHONY: help gen-migrate migrate-up migrate-down migrate-down-all migrate-cloudsql run-migrate-job grant-cloudsql cloudsql-proxy set-quota-project db-up db-down db-del psql require-project require-cloud-project build build-sync deploy build-deploy

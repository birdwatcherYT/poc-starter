.DEFAULT_GOAL := help

# 共有設定は api/.env から取り込む（GOOGLE_CLOUD_PROJECT が真実のソース）。
-include ../api/.env
export

TF_DIR    := terraform
ENV       ?= dev
ENV_DIR   := $(TF_DIR)/env/$(ENV)
TFVARS    := $(ENV_DIR)/terraform.tfvars
ENV_FILE  := ../api/.env

# PROJECT_ID は CLI > 環境変数 > .env(GOOGLE_CLOUD_PROJECT) の順で解決。
PROJECT_ID ?= $(GOOGLE_CLOUD_PROJECT)

# bucket 名はグローバル一意なので PROJECT_ID を含める。
REGION    ?= asia-northeast1
BUCKET    ?= tfstate-poc-starter-$(ENV)-$(PROJECT_ID)

help: ## ヘルプを表示
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

require-project:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID=<your-gcp-project> を指定してください（または先に make set-project PROJECT_ID=<id>）" && exit 1)

set-project: require-project ## PROJECT_ID を api/.env と terraform.tfvars に保存 + gcloud のデフォルトに設定
	@# 1. api/.env の GOOGLE_CLOUD_PROJECT 行を置換（既存なら sed、無ければ append）
	@mkdir -p $(dir $(ENV_FILE))
	@if [ -f $(ENV_FILE) ] && grep -q "^GOOGLE_CLOUD_PROJECT=" $(ENV_FILE); then \
	  sed -i.bak 's|^GOOGLE_CLOUD_PROJECT=.*|GOOGLE_CLOUD_PROJECT=$(PROJECT_ID)|' $(ENV_FILE) && rm $(ENV_FILE).bak; \
	else \
	  echo "GOOGLE_CLOUD_PROJECT=$(PROJECT_ID)" >> $(ENV_FILE); \
	fi
	@echo "updated: $(ENV_FILE) (GOOGLE_CLOUD_PROJECT=$(PROJECT_ID))"
	@# 2. terraform.tfvars の project_id 行のみ書き換え（他の変数行を保持）
	@mkdir -p $(ENV_DIR)
	@if [ -f $(TFVARS) ] && grep -q "^project_id" $(TFVARS); then \
	  sed -i.bak 's|^project_id.*|project_id = "$(PROJECT_ID)"|' $(TFVARS) && rm $(TFVARS).bak; \
	else \
	  echo 'project_id = "$(PROJECT_ID)"' >> $(TFVARS); \
	fi
	@echo "updated: $(TFVARS) (project_id = \"$(PROJECT_ID)\")"
	@# 3. gcloud のデフォルトプロジェクト
	gcloud config set project $(PROJECT_ID)

show-project: ## 現在の PROJECT_ID と関連ファイルの状態を表示
	@echo "ENV          = $(ENV)"
	@echo "PROJECT_ID   = $(PROJECT_ID)"
	@echo "BUCKET       = $(BUCKET)"
	@echo "ENV_FILE     = $(ENV_FILE) ($(shell test -f $(ENV_FILE) && echo exists || echo absent))"
	@echo "TFVARS file  = $(TFVARS) ($(shell test -f $(TFVARS) && echo exists || echo absent))"

create-bucket: require-project ## tfstate 用 GCS bucket を作成（PROJECT_ID 必須、初回のみ）
	gcloud storage buckets create gs://$(BUCKET) \
	  --project=$(PROJECT_ID) \
	  --location=$(REGION) \
	  --uniform-bucket-level-access
	gcloud storage buckets update gs://$(BUCKET) --versioning

fmt: ## terraform fmt -recursive
	terraform fmt -recursive $(TF_DIR)

fmt-check: ## terraform fmt -check -recursive
	terraform fmt -check -recursive $(TF_DIR)

init: require-project ## terraform init (PROJECT_ID 必須、ENV=dev|prod、BUCKET= で上書き可)
	cd $(ENV_DIR) && terraform init -backend-config="bucket=$(BUCKET)"

plan: require-project ## terraform plan (PROJECT_ID 必須、ENV=dev|prod)
	cd $(ENV_DIR) && terraform plan -var="project_id=$(PROJECT_ID)"

apply: require-project ## terraform apply (PROJECT_ID 必須、ENV=dev|prod)
	cd $(ENV_DIR) && terraform apply -var="project_id=$(PROJECT_ID)"

validate: ## terraform validate（CI 用に backend なし）
	cd $(ENV_DIR) && terraform init -backend=false -input=false && terraform validate

.PHONY: help require-project set-project show-project create-bucket fmt fmt-check init plan apply validate

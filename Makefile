.DEFAULT_GOAL := help

help: ## ヘルプを表示
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ----- 複合コマンド（複数コンポーネントを束ねる）-----

api: ## DB を起動して api をローカル起動（db-up + api run）
	$(MAKE) -C database db-up
	$(MAKE) -C api run

api-docker: ## docker compose で DB + api をまとめて起動（migration 適用後）
	$(MAKE) -C database db-up
	$(MAKE) -C api run-docker

# ----- 横断操作（複数コンポーネントにまたがるもの）-----

fmt: ## api / infra のフォーマットをまとめて実行
	$(MAKE) -C api fmt
	$(MAKE) -C infra fmt

# ----- デプロイ（api + migrate-job を束ねる）-----

build: ## Cloud Build に api / migrate を非同期投入（PROJECT_ID 必須）
	$(MAKE) -C api build
	$(MAKE) -C database build

build-sync: ## Cloud Build を同期実行（api → migrate、完了まで待つ）
	$(MAKE) -C api build-sync
	$(MAKE) -C database build-sync

deploy: ## 現在の IMAGE_TAG で Cloud Run サービス / migrate-job を更新
	$(MAKE) -C api deploy
	$(MAKE) -C database deploy

build-deploy: ## 同期ビルド後に api / migrate-job を更新
	$(MAKE) -C api build-deploy
	$(MAKE) -C database build-deploy

.PHONY: help api api-docker fmt build build-sync deploy build-deploy

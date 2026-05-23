# infra/

GCP インフラを Terraform で管理する。

## 構成

```
infra/
├── Makefile
└── terraform/
    ├── modules/   # 共通モジュール（Cloud Run / Cloud SQL / Artifact Registry / Cloud Build SA など）
    └── env/
        ├── dev/   # dev 環境
        └── prod/  # prod 環境（dev/ をコピーして使う）
```

## 前提セットアップ（一度だけ）

### 1. gcloud 認証

```sh
gcloud auth login
gcloud auth application-default login
gcloud config set project <YOUR_PROJECT_ID>
```

### 2. PROJECT_ID を保存 + 任意設定

```sh
make set-project PROJECT_ID=<YOUR_PROJECT_ID>
```

`terraform/env/dev/terraform.tfvars` に書き込み + `gcloud config set project` を実行する。これ以降は `make` ターゲットに `PROJECT_ID=...` を毎回渡さなくてよくなる（tfvars から自動で拾う）。

別環境は `ENV=prod` を付ける: `make set-project PROJECT_ID=<PROD> ENV=prod`

IAP / Cloud SQL の Google Group など任意設定もこの tfvars に追記する。サンプルは [`terraform/env/dev/terraform.tfvars.example`](terraform/env/dev/terraform.tfvars.example) 参照:

```sh
cat terraform/env/dev/terraform.tfvars.example >> terraform/env/dev/terraform.tfvars
# その後エディタで値を埋める（developer_group / allowed_group など）
```

### 3. Terraform state bucket を作成

state は GCS で管理する。bucket は Terraform の外側で先に作る必要がある（chicken-and-egg を避けるため）。bucket 名は GCS のグローバル一意制約があるため `tfstate-poc-starter-$(ENV)-$(PROJECT_ID)` をデフォルトにしている。

```sh
make create-bucket           # set-project 済みなら引数不要
```

bucket 名を独自にしたい場合は `BUCKET=...` で上書き可。

## dev 環境の使い方

```sh
make init     # 初回のみ
make plan
make apply    # 初回は migrate イメージ未作成で Job 更新が失敗することがある（下記参照）
```

`make show-project` で現在の PROJECT_ID / BUCKET / ENV を確認できる。別環境は `ENV=prod` を付ける。その他のターゲットは `make help`。

## image のビルド & デプロイ

`infra/` 側は Artifact Registry リポジトリと Cloud Run リソース定義のみ担当。コンテナイメージ（`api` / `migrate`）は Terraform の外でビルドする。ビルドはルートから呼ぶ。

**初回デプロイの順序（リポジトリルートで実行）:**

```sh
# 1. インフラ作成（Artifact Registry / Cloud Build SA など）
make -C infra apply

# 2. api / migrate イメージをビルド & push
make build-sync IMAGE_TAG=latest

# 3. 作成したイメージを Cloud Run / migrate-job に反映（初回 apply のときは migrate イメージがまだ存在しないため）
make -C infra apply
```

## migration の Cloud SQL への適用

[`../database/README.md`](../database/README.md) を参照。

## API へのアクセス制御

Cloud Run への外部アクセスは `terraform/env/<env>/terraform.tfvars` の `access_mode` と `allowed_group` で決まる（サンプルは [`terraform/env/dev/terraform.tfvars.example`](terraform/env/dev/terraform.tfvars.example)）。

| `access_mode` | 用途 | 挙動 |
|---|---|---|
| `browser`（デフォルト） | ブラウザ | Cloud Run IAP を有効化。Google Group メンバーは OAuth でアクセスできる |
| `terminal` | curl / runner | IAP を無効化し、Group に `roles/run.invoker` を付与。`gcloud auth print-identity-token` の ID token で叩ける |

`allowed_group` が空だと外部からアクセスできない（バインドを作らない）。

[`../api/scripts/`](../api/scripts/) の runner は `BASE_URL=https://...` で Bearer を自動付与する。`terminal` ならそのまま動く。`browser`（IAP）では runner / curl は追加セットアップが必要（[Sharing OAuth clients](https://cloud.google.com/iap/docs/sharing-oauth-clients)）。

## prod 環境

`env/prod/` は雛形のみ。dev をコピーして使う想定:

```sh
cp -r terraform/env/dev/* terraform/env/prod/
# terraform/env/prod/backend.tf の prefix を prod 用に書き換える（例: poc-starter/prod）

make set-project   PROJECT_ID=$PROD_PROJECT_ID ENV=prod
make create-bucket ENV=prod
make init          ENV=prod
make apply         ENV=prod
```

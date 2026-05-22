terraform {
  required_version = ">= 1.6.0"

  # GCS bucket 名はグローバル一意なので、プロジェクトごとに違う値を渡す。
  # 手順は infra/README.md を参照。bucket は `terraform init` の前に gcloud で作成しておく。
  #
  #   terraform init -backend-config="bucket=tfstate-poc-starter-dev-<PROJECT_ID>"
  #
  # （bucket は backend block で必須なので空にできない。プレースホルダを書いておく）
  backend "gcs" {
    bucket = "REPLACE_VIA_BACKEND_CONFIG"
    prefix = "poc-starter/dev"
  }
}

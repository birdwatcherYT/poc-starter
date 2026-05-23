-- アプリ用サービスアカウント（BUILT_IN ユーザー）と開発者向け IAM グループへの
-- 冪等な GRANT。`make cloudsql-grant` または migration Cloud Run Job 経由で実行する。
-- 変数は `psql -v` で渡す（db_name / app_user / dev_group）。

-- アプリ用ユーザーへの権限付与
GRANT CONNECT ON DATABASE :"db_name" TO :"app_user";
GRANT USAGE ON SCHEMA public TO :"app_user";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"app_user";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"app_user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app_user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"app_user";

-- 開発者グループへの権限付与（Cloud SQL IAM 認証で接続）
GRANT CONNECT ON DATABASE :"db_name" TO :"dev_group";
GRANT USAGE ON SCHEMA public TO :"dev_group";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"dev_group";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"dev_group";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"dev_group";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"dev_group";

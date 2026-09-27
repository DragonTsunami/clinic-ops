-- MySQL 首次初始化（仅空数据目录时执行）：监控 exporter 专用最小权限账号
-- 密码与 .env 的 MYSQL_EXPORTER_PASSWORD 保持一致
CREATE USER 'exporter'@'%' IDENTIFIED BY 'exporter_pw' WITH MAX_USER_CONNECTIONS 3;
GRANT PROCESS, REPLICATION CLIENT, SELECT ON *.* TO 'exporter'@'%';
FLUSH PRIVILEGES;

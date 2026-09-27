#!/usr/bin/env bash
# ======================================================================
# 恢复脚本：解密（可选 age）→ 解压 → 灌库。恢复演练核心工具
# 用法：
#   ./restore.sh /backups/clinic_2026-09-27_030000.sql.gz.age   # age 加密件
#   ./restore.sh /backups/clinic_2026-09-27_030000.sql.gz       # 明文件
# 演练流程见 docs/drills/（删库→恢复→数据比对三步）
# ======================================================================
set -euo pipefail

F="$1"
[[ -f "$F" ]] || { echo "备份文件不存在: $F"; exit 1; }

# 1) 还原成明文 sql.gz
TMP_SQL_GZ="$(mktemp /tmp/restore.XXXX.sql.gz)"
trap 'rm -f "$TMP_SQL_GZ"' EXIT
if [[ "$F" == *.age ]]; then
  source /opt/clinic/backup.env   # BACKUP_AGE_PRIVKEY_PATH
  age -d -i "${BACKUP_AGE_PRIVKEY_PATH}" -o "$TMP_SQL_GZ" "$F"
else
  cp "$F" "$TMP_SQL_GZ"
fi

echo ">> 将恢复到容器 clinic-mysql 的 clinic 库，库会被清空重建。${RESTORE_DELAY:-30} 秒内 Ctrl+C 取消。"
sleep "${RESTORE_DELAY:-30}"

# 2) 重建库（drop+create，保证干净恢复）
docker exec clinic-mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS clinic; CREATE DATABASE clinic CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"'

# 3) 灌库
gunzip -c "$TMP_SQL_GZ" | docker exec -i clinic-mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" clinic'

echo ">> 恢复完成。比对行数："
docker exec clinic-mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" clinic -e "SELECT (SELECT COUNT(*) FROM patients) AS patients, (SELECT COUNT(*) FROM appointments) AS appointments;"'

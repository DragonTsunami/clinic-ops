#!/usr/bin/env bash
# ======================================================================
# MySQL 每日备份：mysqldump → gzip → age 加密（医疗叙事：备份静态加密）
# 用法（服务器 crontab）：30 3 * * * /opt/clinic/clinic-ops/ops/backup/backup.sh >> /var/log/clinic-backup.log 2>&1
# 依赖：宿主机装 age（apt install age）；BACKUP_AGE_PUBKEY 在 /opt/clinic/backup.env
# ======================================================================
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # ops/
# 服务器默认 /opt/clinic/backup.env；本地演练用 BACKUP_ENV_FILE 指到仓库内文件
source "${BACKUP_ENV_FILE:-/opt/clinic/backup.env}"

STAMP="$(date +%F_%H%M%S)"
WORK_DIR="${BACKUP_DIR}/tmp"
mkdir -p "${WORK_DIR}"

echo "[$(date '+%F %T')] backup start"

# 1) 导出（容器内 mysqldump，凭据走容器环境变量，不落宿主命令行）
docker exec clinic-mysql sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers clinic' \
  | gzip > "${WORK_DIR}/clinic_${STAMP}.sql.gz"

# 2) 加密（有公钥则 age；无则明文降级并告警式提示——生产必须配公钥）
if [[ -n "${BACKUP_AGE_PUBKEY}" ]] && command -v age >/dev/null; then
  age -r "${BACKUP_AGE_PUBKEY}" -o "${BACKUP_DIR}/clinic_${STAMP}.sql.gz.age" "${WORK_DIR}/clinic_${STAMP}.sql.gz"
  rm "${WORK_DIR}/clinic_${STAMP}.sql.gz"
  echo "[$(date '+%F %T')] encrypted ok: clinic_${STAMP}.sql.gz.age"
else
  mv "${WORK_DIR}/clinic_${STAMP}.sql.gz" "${BACKUP_DIR}/clinic_${STAMP}.sql.gz"
  echo "[$(date '+%F %T')] WARN: age pubkey missing, PLAIN backup saved"
fi

# 3) 本地轮转：保留 N 天
find "${BACKUP_DIR}" -name 'clinic_*.age' -mtime +${BACKUP_KEEP_DAYS:-7} -delete
find "${BACKUP_DIR}" -name 'clinic_*.sql.gz' -mtime +${BACKUP_KEEP_DAYS:-7} -delete

# 4) 异地拷贝（可选）：BACKUP_REMOTE=rclone:xxx 或 scp 目标，留空跳过
if [[ -n "${BACKUP_REMOTE:-}" ]]; then
  for f in "${BACKUP_DIR}"/clinic_${STAMP}.*; do
    # shellcheck disable=SC2086
    rclone copy "$f" "${BACKUP_REMOTE}" 2>/dev/null || scp -q "$f" "${BACKUP_REMOTE}/" || echo "WARN: remote copy failed"
  done
fi

echo "[$(date '+%F %T')] backup done: $(ls -1t "${BACKUP_DIR}"/clinic_* 2>/dev/null | head -1)"

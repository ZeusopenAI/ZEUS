#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Zeus / Quang Quý AI — backup $HERMES_HOME của Hermes Gateway
#
# Backup gồm: config, memory, sessions, DB nội bộ (đầu vào của bộ não thứ hai).
# Loại ra: log, cache — tái tạo được, không đáng lưu.
# Nếu đặt biến HERMES_BACKUP_AGE_PUBKEY (recipient age) thì bản backup được
# mã hoá age; nếu không, bản backup là tar.gz PLAIN — chỉ lưu tại nơi riêng tư.
#
# Cách dùng:
#   bash deploy/vps/backup-hermes.sh                 # backup + xoay giữ 7 bản
#   KEEP=30 bash deploy/vps/backup-hermes.sh         # giữ 30 bản
#   HERMES_BACKUP_AGE_PUBKEY=age1... bash deploy/vps/backup-hermes.sh
#
# Khuyến nghị: crontab mỗi ngày lúc 03:00
#   0 3 * * * /opt/zeus/deploy/vps/backup-hermes.sh >> /home/hermes/.hermes/backup.log 2>&1
# SAU ĐÓ copy bản backup ra ngoài VPS (rclone/scp) — backup nằm cùng máy
# thì khi mất máy là mất cả hai. Quy trình khôi phục: docs/RUNBOOK_247.md
# ============================================================================

HERMES_HOME="${HERMES_HOME:-/home/hermes/.hermes}"
BACKUP_DIR="${BACKUP_DIR:-${HERMES_HOME}/backups}"
KEEP="${KEEP:-7}"
STAMP="$(date +%Y%m%d-%H%M%S)"
HOST_TAG="$(hostname -s 2>/dev/null || echo host)"

if [ "$(id -u)" -eq 0 ]; then
  OWN="--owner=hermes --group=hermes"
else
  OWN=""
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR" 2>/dev/null || true

OUT_BASE="${BACKUP_DIR}/hermes-${HOST_TAG}-${STAMP}.tar"

echo "[backup] gom ${HERMES_HOME} ..."
# --exclude theo đường dẫn tương đối trong archive
tar --create --absolute-names "$OWN" \
    --exclude="${HERMES_HOME}/logs" \
    --exclude="${HERMES_HOME}/cache" \
    --exclude="${HERMES_HOME}/backups" \
    --file "${OUT_BASE}" \
    "${HERMES_HOME}" 2>/dev/null

if [ -n "${HERMES_BACKUP_AGE_PUBKEY:-}" ]; then
  if ! command -v age >/dev/null 2>&1; then
    echo "ERROR: cần 'age' để mã hoá (apt install age) hoặc bỏ HERMES_BACKUP_AGE_PUBKEY." >&2
    rm -f "${OUT_BASE}"
    exit 1
  fi
  age -r "$HERMES_BACKUP_AGE_PUBKEY" -o "${OUT_BASE}.age" "${OUT_BASE}"
  rm -f "${OUT_BASE}"
  OUT="${OUT_BASE}.age"
else
  OUT="${OUT_BASE}"
fi

chmod 600 "$OUT" 2>/dev/null || true
echo "[backup] xong: ${OUT} ($(du -h "$OUT" | cut -f1))"

echo "[backup] xoay bản cũ, giữ ${KEEP} bản gần nhất ..."
ls -1t "${BACKUP_DIR}"/hermes-*.tar* 2>/dev/null | tail -n +$((KEEP+1)) | while read -r old; do
  rm -f "$old"
  echo "[backup] đã xoá: ${old}"
done

echo "[backup] danh sách hiện tại:"
ls -lh "${BACKUP_DIR}"/hermes-*.tar* 2>/dev/null || true

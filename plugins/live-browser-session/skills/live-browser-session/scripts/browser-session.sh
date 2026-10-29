#!/usr/bin/env bash
# 전용 프로필 Chrome을 원격 디버깅(CDP)으로 열고, 확인하고, 닫은 뒤 프로필을 지운다.
#   start  <URL>         새 임시 프로필로 Chrome을 연다. 사용자가 이 창에서 직접 로그인한다.
#   status               열린 탭의 제목·주소를 보여 준다.
#   stop   --profile DIR Chrome을 닫고, start가 만든 프로필이면 지운다.
# 환경변수: LBS_PORT(기본 9333), CHROME_BIN(Chrome 실행 파일 경로)
set -euo pipefail

MARKER=".live-browser-session"
PORT="${LBS_PORT:-9333}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() { sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }
cdp_up() { curl -s --max-time 2 "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; }

chrome_bin() {
  if [ -n "${CHROME_BIN:-}" ]; then echo "${CHROME_BIN}"; return 0; fi
  local c
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           google-chrome google-chrome-stable chromium chromium-browser; do
    if [ -x "${c}" ] || command -v "${c}" >/dev/null 2>&1; then echo "${c}"; return 0; fi
  done
  return 1
}

start() {
  local url="${1:-about:blank}" bin profile pid i
  bin="$(chrome_bin)" || { echo "Chrome을 찾지 못했습니다. CHROME_BIN을 지정하세요." >&2; exit 1; }
  if cdp_up; then echo "포트 ${PORT}에 이미 원격 디버깅 브라우저가 있습니다. stop 후 다시 시작하거나 LBS_PORT를 바꾸세요." >&2; exit 1; fi
  local tmp="${TMPDIR:-/tmp}"
  profile="$(mktemp -d "${tmp%/}/live-browser-session.XXXXXX")"
  # 원격 디버깅은 127.0.0.1에만 열린다(Chrome 기본값). 다른 주소로 열지 않는다.
  nohup "${bin}" --remote-debugging-port="${PORT}" --user-data-dir="${profile}" \
    --no-first-run --no-default-browser-check --window-size=1440,960 "${url}" >/dev/null 2>&1 &
  pid=$!
  echo "${pid}" > "${profile}/${MARKER}"
  for i in $(seq 1 30); do cdp_up && break; sleep 0.5; done
  cdp_up || { echo "Chrome 원격 디버깅 포트가 열리지 않았습니다." >&2; exit 1; }
  echo "port=${PORT}"
  echo "profile=${profile}"
  echo "pid=${pid}"
  echo "이 창에서 사용자가 직접 로그인한 뒤 작업을 시작합니다. 끝나면: $0 stop --profile ${profile}"
}

status() {
  cdp_up || { echo "포트 ${PORT}에 열린 브라우저가 없습니다."; exit 1; }
  curl -s "http://127.0.0.1:${PORT}/json/version" | grep '"Browser"' || true
  # 일반 탭(page)만 보여 준다. Chrome 내부 화면은 뺀다.
  curl -s "http://127.0.0.1:${PORT}/json/list" | python3 -c 'import json,sys
for t in json.load(sys.stdin):
    if t.get("type") == "page": print(t.get("title", ""), "|", t.get("url", ""))' 2>/dev/null \
    || curl -s "http://127.0.0.1:${PORT}/json/list" | grep -E '"(title|url)"' || true
}

stop() {
  local profile="" pid="" i
  while [ $# -gt 0 ]; do
    case "$1" in
      --profile) profile="${2:-}"; shift 2 ;;
      *) echo "알 수 없는 옵션: $1" >&2; usage 2 ;;
    esac
  done
  [ -n "${profile}" ] || { echo "--profile DIR가 필요합니다(start가 출력한 profile)." >&2; exit 2; }
  [ -d "${profile}" ] || { echo "프로필 폴더가 없습니다: ${profile}" >&2; exit 1; }
  # start가 만든 폴더만 지운다. 표시 파일이 없으면 사용자의 다른 폴더일 수 있으므로 멈춘다.
  [ -f "${profile}/${MARKER}" ] || { echo "${profile}에 ${MARKER}가 없어 지우지 않습니다." >&2; exit 1; }
  pid="$(cat "${profile}/${MARKER}" 2>/dev/null || true)"

  if cdp_up; then
    node "${HERE}/cdp-close.mjs" "${PORT}" 2>/dev/null || true
  fi
  for i in $(seq 1 20); do cdp_up || break; sleep 0.5; done
  if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}" 2>/dev/null || true
    for i in $(seq 1 20); do kill -0 "${pid}" 2>/dev/null || break; sleep 0.5; done
  fi
  if cdp_up || { [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; }; then
    echo "Chrome이 아직 실행 중이라 프로필을 지우지 않았습니다(pid=${pid}). 창을 닫은 뒤 다시 실행하세요." >&2
    exit 1
  fi
  rm -rf "${profile:?}"
  echo "closed=yes"
  echo "profile_deleted=${profile}"
}

case "${1:-}" in
  start) shift; start "$@" ;;
  status) shift; status ;;
  stop) shift; stop "$@" ;;
  -h|--help|"") usage 0 ;;
  *) echo "알 수 없는 명령: $1" >&2; usage 2 ;;
esac

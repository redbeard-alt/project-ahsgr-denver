#!/usr/bin/env bash
# launchd/install.sh — install/remove the AHSGR exec-assistant brief jobs.
#
#   bash launchd/install.sh           # install (06:00 + 17:00, weekdays)
#   bash launchd/install.sh --unload  # stop + remove
#
# Paths are substituted dynamically (no hardcoded user paths). The jobs run a
# DEDICATED venv at ~/.venvs/ahsgr-brief — create it first:
#   python3 -m venv ~/.venvs/ahsgr-brief
#   ~/.venvs/ahsgr-brief/bin/pip install -r lib/briefing/requirements.txt
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PY="${HOME}/.venvs/ahsgr-brief/bin/python"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/ahsgr-brief"
PLISTS=("com.ahsgr.brief.morning.plist" "com.ahsgr.brief.eod.plist")

if [[ "${1:-}" == "--unload" ]]; then
    echo "Unloading AHSGR brief jobs…"
    for plist in "${PLISTS[@]}"; do
        dst="${LAUNCH_AGENTS_DIR}/${plist}"; label="${plist%.plist}"
        launchctl bootout "gui/$(id -u)" "${dst}" 2>/dev/null && echo "  [unloaded] ${label}" \
            || echo "  [skip] ${label} not loaded"
        [[ -f "${dst}" ]] && rm "${dst}" && echo "  [removed] ${dst}"
    done
    echo "Done."
    exit 0
fi

# ── Install ──────────────────────────────────────────────────────────────────
if [[ ! -x "${VENV_PY}" ]]; then
    echo "ERROR: brief venv not found at ${VENV_PY}"
    echo "  Run: python3 -m venv ~/.venvs/ahsgr-brief && \\"
    echo "       ~/.venvs/ahsgr-brief/bin/pip install -r ${REPO_ROOT}/lib/briefing/requirements.txt"
    exit 1
fi
if [[ ! -f "${REPO_ROOT}/.env" ]]; then
    echo "WARNING: ${REPO_ROOT}/.env not found — delivery will be skipped until DISCORD_WEBHOOK_URL is set."
fi

mkdir -p "${LAUNCH_AGENTS_DIR}" "${LOG_DIR}"
echo "Installing AHSGR brief jobs…"
echo "  Repo : ${REPO_ROOT}"
echo "  Venv : ${VENV_PY}"
echo "  Logs : ${LOG_DIR}"

for plist in "${PLISTS[@]}"; do
    src="${SCRIPT_DIR}/${plist}"; dst="${LAUNCH_AGENTS_DIR}/${plist}"; label="${plist%.plist}"
    sed -e "s|VENV_PY|${VENV_PY}|g" -e "s|REPO_ROOT|${REPO_ROOT}|g" -e "s|HOME|${HOME}|g" \
        "${src}" > "${dst}"
    echo "  [copied] ${plist}"
    launchctl bootout "gui/$(id -u)" "${dst}" 2>/dev/null || true   # reload if already loaded
    launchctl bootstrap "gui/$(id -u)" "${dst}"
    echo "  [loaded] ${label}"
done

echo ""
echo "Done. Morning 06:00, EOD 17:00 (weekdays)."
echo "  status : launchctl list | grep ahsgr.brief"
echo "  unload : bash launchd/install.sh --unload"

#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/starsnatched/super-system.git"
INSTALL_DIR="${HOME}/.local/share/super-system"

info()  { printf '\033[1;34m=>\033[0m %s\n' "$*"; }
ok()    { printf '\033[1;32m✓\033[0m  %s\n' "$*"; }
fail()  { printf '\033[1;31m✗\033[0m  %s\n' "$*" >&2; exit 1; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

if ! command_exists git; then
    fail "git is required but not installed."
fi

if ! command_exists uv; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
    command_exists uv || fail "uv installation failed."
    ok "uv installed"
else
    ok "uv found at $(command -v uv)"
fi

if [ -d "${INSTALL_DIR}/.git" ]; then
    info "Updating existing clone..."
    git -C "${INSTALL_DIR}" pull --ff-only
else
    info "Cloning super-system..."
    rm -rf "${INSTALL_DIR}"
    git clone "${REPO}" "${INSTALL_DIR}"
fi
ok "Source ready at ${INSTALL_DIR}"

info "Installing super-system CLI..."
uv tool install --editable "${INSTALL_DIR}" --force
ok "Installed"

if ! echo "${PATH}" | grep -q "${HOME}/.local/bin"; then
    SHELL_NAME="$(basename "${SHELL}")"
    case "${SHELL_NAME}" in
        zsh)  RC="${HOME}/.zshrc" ;;
        bash) RC="${HOME}/.bashrc" ;;
        fish) RC="${HOME}/.config/fish/config.fish" ;;
        *)    RC="" ;;
    esac
    if [ -n "${RC}" ] && [ -f "${RC}" ]; then
        if ! grep -q '\.local/bin' "${RC}" 2>/dev/null; then
            info "Adding ~/.local/bin to PATH in ${RC}..."
            printf '\nexport PATH="${HOME}/.local/bin:${PATH}"\n' >> "${RC}"
            ok "PATH updated — restart your shell or run: source ${RC}"
        fi
    else
        printf '\n\033[1;33m!\033[0m  Add ~/.local/bin to your PATH manually.\n'
    fi
fi

printf '\n\033[1;32msuper-system is ready.\033[0m\n'
printf '  Run \033[1msuper-system\033[0m from any directory to launch the TUI.\n'
printf '  Your API key will be prompted on first launch.\n\n'

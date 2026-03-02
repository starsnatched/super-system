#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/starsnatched/super-system.git"
INSTALL_DIR="${HOME}/.local/share/super-system"

info()  { printf '\033[1;34m=>\033[0m %s\n' "$*"; }
ok()    { printf '\033[1;32m✓\033[0m  %s\n' "$*"; }
warn()  { printf '\033[1;33m!\033[0m  %s\n' "$*"; }
fail()  { printf '\033[1;31m✗\033[0m  %s\n' "$*" >&2; exit 1; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

if ! command_exists git; then
    fail "git is required but not installed."
fi

# --- uv (Python toolchain) ---

if ! command_exists uv; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
    command_exists uv || fail "uv installation failed."
    ok "uv installed"
else
    ok "uv found at $(command -v uv)"
fi

# --- npm (Node.js package manager) ---

ensure_npm() {
    if command_exists npm; then
        ok "npm found at $(command -v npm)"
        return 0
    fi

    if command_exists bun; then
        ok "bun found at $(command -v bun) (will use for global installs)"
        return 0
    fi

    info "npm not found — installing Node.js via uv..."
    if uv tool install nodejs --force >/dev/null 2>&1 && command_exists npm; then
        ok "Node.js installed via uv"
        return 0
    fi

    info "Trying nvm..."
    export NVM_DIR="${HOME}/.nvm"
    if [ ! -d "${NVM_DIR}" ]; then
        curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    fi
    [ -s "${NVM_DIR}/nvm.sh" ] && . "${NVM_DIR}/nvm.sh"
    if command_exists nvm; then
        nvm install --lts >/dev/null 2>&1
        nvm use --lts >/dev/null 2>&1
        if command_exists npm; then
            ok "Node.js installed via nvm"
            return 0
        fi
    fi

    if [ "$(uname -s)" = "Darwin" ] && command_exists brew; then
        info "Trying Homebrew..."
        brew install node >/dev/null 2>&1
        if command_exists npm; then
            ok "Node.js installed via Homebrew"
            return 0
        fi
    fi

    warn "Could not install npm automatically."
    warn "Install Node.js manually: https://nodejs.org"
    return 1
}

ensure_npm
HAS_NPM=$?

# --- Helper: install a global npm package ---

npm_global_install() {
    local pkg="$1"
    local cmd="$2"

    if command_exists "${cmd}"; then
        ok "${cmd} already installed at $(command -v "${cmd}")"
        return 0
    fi

    if [ "${HAS_NPM}" -ne 0 ]; then
        warn "Skipping ${pkg} — npm/bun not available"
        return 1
    fi

    info "Installing ${pkg}..."
    if command_exists bun; then
        bun install -g "${pkg}" >/dev/null 2>&1
    else
        npm install -g "${pkg}" >/dev/null 2>&1
    fi

    if command_exists "${cmd}"; then
        ok "${cmd} installed"
        return 0
    else
        warn "${cmd} install completed but command not found in PATH"
        return 1
    fi
}

# --- Clone / update super-system ---

if [ -d "${INSTALL_DIR}/.git" ]; then
    info "Updating existing clone..."
    git -C "${INSTALL_DIR}" pull --ff-only
else
    info "Cloning super-system..."
    rm -rf "${INSTALL_DIR}"
    git clone "${REPO}" "${INSTALL_DIR}"
fi
ok "Source ready at ${INSTALL_DIR}"

# --- Install super-system CLI ---

info "Installing super-system CLI..."
uv tool install --editable "${INSTALL_DIR}" --force
ok "Installed"

# --- Install UX design skill dependencies ---

npm_global_install "memex-cli" "memex-cli"
npm_global_install "@google/gemini-cli" "gemini"

# --- Initialize UX design skill (Gemini API key) ---

CONFIG_DIR="${HOME}/.config/super-system"
CONFIG_FILE="${CONFIG_DIR}/config.json"

read_config_key() {
    local key="$1"
    if [ -f "${CONFIG_FILE}" ]; then
        python3 -c "import json,sys; c=json.load(open('${CONFIG_FILE}')); print(c.get('${key}',''))" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

write_config_key() {
    local key="$1"
    local value="$2"
    mkdir -p "${CONFIG_DIR}"
    if [ -f "${CONFIG_FILE}" ]; then
        python3 -c "
import json, sys
with open('${CONFIG_FILE}') as f: c = json.load(f)
c['${key}'] = '${value}'
with open('${CONFIG_FILE}', 'w') as f: json.dump(c, f, indent=2)
" 2>/dev/null
    else
        printf '{\n  "%s": "%s"\n}\n' "${key}" "${value}" > "${CONFIG_FILE}"
    fi
}

GEMINI_CONFIGURED=false

if [ -n "${GEMINI_API_KEY:-}" ]; then
    ok "GEMINI_API_KEY already set in environment"
    GEMINI_CONFIGURED=true
elif [ -n "$(read_config_key gemini_api_key)" ]; then
    ok "Gemini API key already configured in ${CONFIG_FILE}"
    GEMINI_CONFIGURED=true
fi

if [ "${GEMINI_CONFIGURED}" = false ]; then
    printf '\n'
    info "UX Design Skill Setup (ux-design-gemini)"
    printf '  The UX design skill uses Google Gemini for design generation.\n'
    printf '  You can authenticate via API key or Google OAuth.\n\n'
    printf '  \033[1m1)\033[0m Enter a Gemini API key (get one at https://aistudio.google.com/apikey)\n'
    printf '  \033[1m2)\033[0m Skip — authenticate later by running \033[1mgemini\033[0m or setting GEMINI_API_KEY\n\n'

    if [ -t 0 ]; then
        printf '  Gemini API key (or press Enter to skip): '
        read -r GEMINI_KEY_INPUT
        if [ -n "${GEMINI_KEY_INPUT}" ]; then
            write_config_key "gemini_api_key" "${GEMINI_KEY_INPUT}"
            ok "Gemini API key saved to ${CONFIG_FILE}"

            SHELL_NAME="$(basename "${SHELL}")"
            case "${SHELL_NAME}" in
                zsh)  RC="${HOME}/.zshrc" ;;
                bash) RC="${HOME}/.bashrc" ;;
                *)    RC="" ;;
            esac
            if [ -n "${RC}" ] && [ -f "${RC}" ]; then
                if ! grep -q 'GEMINI_API_KEY' "${RC}" 2>/dev/null; then
                    printf '\nexport GEMINI_API_KEY="%s"\n' "${GEMINI_KEY_INPUT}" >> "${RC}"
                    ok "GEMINI_API_KEY added to ${RC}"
                fi
            fi
            GEMINI_CONFIGURED=true
        else
            warn "Skipped — set up Gemini auth later"
        fi
    else
        warn "Non-interactive shell — skipping Gemini API key prompt"
        warn "Set GEMINI_API_KEY or run: gemini (OAuth login)"
    fi
fi

# --- PATH setup ---

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
        warn "Add ~/.local/bin to your PATH manually."
    fi
fi

printf '\n\033[1;32msuper-system is ready.\033[0m\n'
printf '  Run \033[1msuper-system\033[0m from any directory to launch the TUI.\n'
printf '  Your Anthropic API key will be prompted on first launch.\n'
if [ "${GEMINI_CONFIGURED}" = true ]; then
    ok "UX design skill (ux-design-gemini) is configured and ready"
else
    printf '  To enable the UX design skill, do one of:\n'
    printf '    • Run \033[1mgemini\033[0m to authenticate via Google OAuth (free)\n'
    printf '    • Set \033[1mGEMINI_API_KEY\033[0m in your environment\n'
fi
printf '\n'

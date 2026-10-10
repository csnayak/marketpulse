#!/usr/bin/env bash
# Install Docker Engine from Docker's official
# Ubuntu APT repository. Intended for Ubuntu/Ubuntu on WSL, not Docker Desktop.
# Official instructions: https://docs.docker.com/engine/install/ubuntu/

set -Eeuo pipefail

log() { printf '\n==> %s\n' "$*"; }
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }

[[ -r /etc/os-release ]] || die 'Cannot identify this operating system.'
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == ubuntu ]] || die "This installer supports Ubuntu only (detected: ${ID:-unknown})."

codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
case "$codename" in
  jammy|noble|resolute) ;;
  *) die "Unsupported Ubuntu release '${codename:-unknown}'. Check Docker's current Ubuntu support before proceeding." ;;
esac

arch="$(dpkg --print-architecture)"
case "$arch" in
  amd64|arm64|armhf|s390x|ppc64el) ;;
  *) die "Unsupported package architecture: $arch" ;;
esac

if [[ "$EUID" -eq 0 ]]; then
  SUDO=()
else
  command -v sudo >/dev/null 2>&1 || die 'sudo is required. Install sudo or run this script as root.'
  SUDO=(sudo)
fi

# Avoid silently removing distro packages or another container runtime.
conflicts=()
for package in docker.io docker-doc podman-docker containerd runc; do
  if dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null | grep -qx 'installed'; then
    conflicts+=("$package")
  fi
done
if ((${#conflicts[@]})); then
  printf 'Found packages that may conflict with Docker CE: %s\n' "${conflicts[*]}" >&2
  printf 'Review Docker\x27s uninstall guidance before removing or replacing them:\n' >&2
  printf 'https://docs.docker.com/engine/install/ubuntu/#uninstall-old-versions\n' >&2
  die 'No packages were removed. Resolve the conflict, then rerun this installer.'
fi

log 'Install APT prerequisites'
"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y ca-certificates curl

log 'Configure Docker official APT signing key and repository'
"${SUDO[@]}" install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | "${SUDO[@]}" tee /etc/apt/keyrings/docker.asc >/dev/null
"${SUDO[@]}" chmod a+r /etc/apt/keyrings/docker.asc

"${SUDO[@]}" tee /etc/apt/sources.list.d/docker.sources >/dev/null <<REPO
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${codename}
Components: stable
Architectures: ${arch}
Signed-By: /etc/apt/keyrings/docker.asc
REPO

log 'Install Docker Engine, CLI, container runtime, and Buildx'
"${SUDO[@]}" apt-get update
"${SUDO[@]}" apt-get install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin

log 'Check installed versions'
docker --version

if [[ "$(ps -p 1 -o comm= 2>/dev/null | tr -d ' ')" == systemd ]] \
  && command -v systemctl >/dev/null 2>&1; then
  log 'Enable and start the Docker daemon'
  "${SUDO[@]}" systemctl enable --now docker
  "${SUDO[@]}" docker info >/dev/null
  printf '\nDocker Engine is installed and running. Try: sudo docker run hello-world\n'
else
  cat <<'MESSAGE'
Docker Engine is installed, but this Ubuntu session is not running systemd,
so the docker.service could not be started here.

For WSL, enable systemd by adding this section to /etc/wsl.conf (preserve any
existing sections):

  [boot]
  systemd=true

Then, from Windows PowerShell, run: wsl --shutdown
Reopen Ubuntu and run: sudo systemctl enable --now docker
Verify with: sudo docker info
MESSAGE
fi

cat <<'NEXT'

Docker commands may require sudo. This installer does not add your account to
the docker group because that grants root-equivalent access. Install Terraform,
then use the Terraform configuration to start MarketPulse:

  terraform -chdir=terraform init
  terraform -chdir=terraform apply
NEXT

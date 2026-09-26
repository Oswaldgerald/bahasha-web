#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Build and push the Bahasha production image to Docker Hub.

Usage:
  DOCKERHUB_REPO=gezward/bahasha ./scripts/push-dockerhub.sh [tag]

Examples:
  DOCKERHUB_REPO=gezward/bahasha ./scripts/push-dockerhub.sh v1.0.0
  DOCKERHUB_REPO=gezward/bahasha PLATFORM=linux/arm64 ./scripts/push-dockerhub.sh 2026-07-03

Environment:
  DOCKERHUB_REPO  Required. Docker Hub repository, for example gezward/bahasha.
  PLATFORM        Optional. Defaults to linux/amd64 for typical Ubuntu servers.
  DOCKERFILE      Optional. Defaults to Dockerfile.
  CONTEXT         Optional. Defaults to current directory.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${DOCKERHUB_REPO:-}" ]]; then
  echo "ERROR: DOCKERHUB_REPO is required." >&2
  usage >&2
  exit 1
fi

TAG="${1:-$(date +%Y%m%d%H%M%S)}"
PLATFORM="${PLATFORM:-linux/amd64}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"
CONTEXT="${CONTEXT:-.}"

if ! docker buildx version >/dev/null 2>&1; then
  echo "ERROR: docker buildx is required." >&2
  exit 1
fi

echo "Building and pushing:"
echo "  ${DOCKERHUB_REPO}:${TAG}"
echo "  ${DOCKERHUB_REPO}:latest"
echo "Platform: ${PLATFORM}"

docker buildx build \
  --platform "${PLATFORM}" \
  --file "${DOCKERFILE}" \
  --tag "${DOCKERHUB_REPO}:${TAG}" \
  --tag "${DOCKERHUB_REPO}:latest" \
  --push \
  "${CONTEXT}"

echo "Pushed ${DOCKERHUB_REPO}:${TAG} and ${DOCKERHUB_REPO}:latest"

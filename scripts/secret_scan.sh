#!/bin/sh
set -eu

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  tracked_files="$(git ls-files)"
else
  tracked_files="$(find . -type f \
    ! -path '*/.git/*' \
    ! -path '*/node_modules/*' \
    ! -path '*/.next/*' \
    ! -path '*/venv/*' \
    ! -path '*/.venv/*' \
    ! -path '*/.venv_test/*' \
    ! -path '*/__pycache__/*')"
fi

forbidden_files="$(printf '%s\n' "$tracked_files" | grep -E '(^|/)(\.env|\.env\..*|kaggle\.json|.*service-account.*\.json|.*key.*\.json)$' | grep -Ev '(^|/)\.env\.example$' || true)"
if [ -n "$forbidden_files" ]; then
  echo "Forbidden secret-bearing files are present:"
  echo "$forbidden_files"
  exit 1
fi

secret_hits="$(
  printf '%s\n' "$tracked_files" \
    | grep -Ev '(^|/)(node_modules|\.next|venv|\.venv|\.venv_test|__pycache__|backend/Alpha/models|backend/Beta/models|backend/Alpha/outputs|backend/Beta/outputs|backend/Beta/jay_test|backend/Beta/test_files)/' \
    | grep -Ev '\.(png|jpg|jpeg|gif|webp|safetensors|zip|pyc|ipynb|csv|lock)$' \
    | xargs grep -nE '(AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----)' 2>/dev/null || true
)"

if [ -n "$secret_hits" ]; then
  echo "Potential hard-coded secrets detected:"
  echo "$secret_hits"
  exit 1
fi

echo "Secret scan passed"

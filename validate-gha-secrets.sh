#!/usr/bin/env bash
# validate-gha-secrets.sh — Verify GHA repo secrets match Infisical production values
# Usage: ./validate-gha-secrets.sh
# Requires: gh CLI, infisical CLI (authenticated), jq

set -euo pipefail

INFISICAL_PROJECT="bd272d48-c5a1-4b52-9d24-12066ae4403c"
ENV="prod"

# Known mappings: GHA_SECRET_NAME:INFISICAL_SECRET_NAME:REPO
MAPPINGS=(
  "AIM_TEST_API_KEY:INTERNAL_API_KEY:aidotmarket/aim-node"
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo "=== GHA ↔ Infisical Secret Validation ==="
echo ""

errors=0
for mapping in "${MAPPINGS[@]}"; do
  IFS=':' read -r gha_name inf_name repo <<< "$mapping"
  
  # Get Infisical value
  inf_val=$(infisical secrets get "$inf_name" --env="$ENV" --projectId="$INFISICAL_PROJECT" --plain 2>/dev/null || echo "INFISICAL_ERROR")
  
  if [[ "$inf_val" == "INFISICAL_ERROR" ]]; then
    echo -e "${RED}✗${NC} $repo/$gha_name — cannot read Infisical secret $inf_name"
    ((errors++))
    continue
  fi
  
  # GHA secrets are write-only, can't read values. Best we can do:
  # Set the secret to the Infisical value (idempotent)
  echo "$inf_val" | gh secret set "$gha_name" --repo="$repo" 2>/dev/null
  if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✓${NC} $repo/$gha_name synced to Infisical $inf_name"
  else
    echo -e "${RED}✗${NC} $repo/$gha_name — failed to sync"
    ((errors++))
  fi
done

echo ""
if [[ $errors -eq 0 ]]; then
  echo -e "${GREEN}All secrets synced.${NC}"
else
  echo -e "${YELLOW}$errors secret(s) had issues.${NC}"
  exit 1
fi

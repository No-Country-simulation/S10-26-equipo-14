
#!/usr/bin/env bash
set -euo pipefail

REPO="No-Country-simulation/S10-26-equipo-14"

if [[ $# -lt 2 ]]; then
  echo "Uso: bash scripts/crear-rama-issue.sh PS-005 store-migrations"
  exit 1
fi

PS_ID="$1"
SLUG="$2"

gh auth status
gh repo view "$REPO" >/dev/null

# Encontrar el número real del issue a partir de la clave PS.
ISSUE_NUMBER="$(
  gh issue list --repo "$REPO" --state all --limit 1000 \
    --json number,title \
    --jq ".[] | select(.title | startswith(\"[$PS_ID]\")) | .number" \
    | head -n 1
)"

if [[ -z "$ISSUE_NUMBER" ]]; then
  echo "No se encontró un issue con el identificador $PS_ID"
  exit 1
fi

BRANCH="feature/${PS_ID,,}-${SLUG}"

echo "Issue: #$ISSUE_NUMBER"
echo "Rama:  $BRANCH"
echo "Base:  develop"

gh issue develop "$ISSUE_NUMBER" \
  --repo "$REPO" \
  --base develop \
  --name "$BRANCH" \
  --checkout

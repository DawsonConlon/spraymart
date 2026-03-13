#!/usr/bin/env bash
# Run this once locally to push the project to a new GitLab repo.
# Usage: ./scripts/init_gitlab_repo.sh https://gitlab.com/yourgroup/agrispray.git

set -e

REMOTE="${1:-}"

if [ -z "$REMOTE" ]; then
  echo "Usage: $0 <gitlab-repo-url>"
  echo "Example: $0 https://gitlab.com/yourgroup/agrispray.git"
  exit 1
fi

cd "$(dirname "$0")/.."

git init
git checkout -b main
git add .
git commit -m "feat: initial AgriSpray backend scaffold

- FastAPI app with field management and recommendation endpoints
- GDD engine: accumulates growing degree days from plant date
- Plant stage evaluator: maps GDD + sunlight hours to growth stage
- Spray scorer: evaluates wind, temp, humidity, rain, inversion risk
- Recommendation engine: combines stage + conditions into SPRAY NOW / WAIT / DO NOT SPRAY
- Environment Canada weather client (current + historical + forecast)
- PostgreSQL models: Farm, Field, SprayEvent
- Unit tests for GDD engine and spray scorer
- Docker + docker-compose with TimescaleDB
- GitLab CI: test → build → deploy pipeline"

git remote add origin "$REMOTE"
git push -u origin main

echo ""
echo "Done. Repo pushed to $REMOTE"
echo "Visit your GitLab project to confirm the pipeline is running."

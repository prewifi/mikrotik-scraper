#!/bin/bash
# setup-dev.sh - Script di setup per development environment
# Uso: bash scripts/setup-dev.sh

set -e

echo "🚀 Setup Development Environment..."

# Colori per output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}1️⃣  Building development container...${NC}"
docker compose -f compose.dev.yaml build

echo -e "${BLUE}2️⃣  Starting development container...${NC}"
docker compose -f compose.dev.yaml up -d ubiquiti-automation-dev

echo -e "${BLUE}3️⃣  Configuring git inside the container...${NC}"
docker compose -f compose.dev.yaml exec ubiquiti-automation-dev \
  bash -c "git config --global user.email 'dev@ubiquiti-automation.local' && git config --global user.name 'Development User'"

echo -e "${BLUE}4️⃣  Installing pre-commit hooks...${NC}"
docker compose -f compose.dev.yaml exec ubiquiti-automation-dev \
  bash -c "pre-commit install && pre-commit install --hook-type commit-msg"

echo -e "${BLUE}5️⃣  Running initial checks...${NC}"
docker compose -f compose.dev.yaml exec ubiquiti-automation-dev \
  bash -c "black --check src/ tests/ || true && flake8 src/ tests/ || true"

echo -e "${BLUE}6️⃣  Running tests...${NC}"
docker compose -f compose.dev.yaml exec ubiquiti-automation-dev \
  bash -c "pytest tests/ -v --tb=short || true"

echo -e "${GREEN}✅ Development environment setup complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Access the container: docker compose -f compose.dev.yaml exec ubiquiti-automation-dev bash"
echo "2. Make changes and commit: cz commit"
echo "3. Run tests: pytest"
echo "4. Format code: black src/"
echo "5. Check types: mypy src/"

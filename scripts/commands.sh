#!/bin/bash
# Makefile-like script per comandi comuni
# Uso: bash scripts/commands.sh [comando]

set -e

case "$1" in
  "dev:start")
    echo "Starting development environment..."
    docker compose -f compose.dev.yaml up -d mikrotik-scraper-dev
    echo "Container started. Access with: docker compose -f compose.dev.yaml exec mikrotik-scraper-dev bash"
    ;;

  "dev:stop")
    echo "Stopping development environment..."
    docker compose -f compose.dev.yaml down
    ;;

  "dev:rebuild")
    echo "Rebuilding development image..."
    docker compose -f compose.dev.yaml build --no-cache
    docker compose -f compose.dev.yaml up -d mikrotik-scraper-dev
    ;;

  "dev:bash")
    docker compose -f compose.dev.yaml exec mikrotik-scraper-dev bash
    ;;

  "prod:start")
    echo "Starting production environment..."
    docker compose -f compose.prod.yaml up -d
    echo "Production started. Logs:"
    docker compose -f compose.prod.yaml logs -f
    ;;

  "prod:stop")
    echo "Stopping production environment..."
    docker compose -f compose.prod.yaml down
    ;;

  "test")
    echo "Running tests..."
    docker compose -f compose.dev.yaml exec mikrotik-scraper-dev pytest tests/ -v --tb=short
    ;;

  "lint")
    echo "Running linters..."
    docker compose -f compose.dev.yaml exec mikrotik-scraper-dev bash -c "black --check src/ && flake8 src/ && mypy src/"
    ;;

  "format")
    echo "Formatting code..."
    docker compose -f compose.dev.yaml exec mikrotik-scraper-dev bash -c "black src/ && isort src/"
    ;;

  "commit")
    echo "Starting interactive commit..."
    docker compose -f compose.dev.yaml exec mikrotik-scraper-dev cz commit
    ;;

  "run:inventory")
    echo "Running inventory collection with config.yaml..."
    docker compose -f compose.dev.yaml exec mikrotik-scraper-dev python3 src/main.py -c config.yaml
    ;;

  "logs:dev")
    docker compose -f compose.dev.yaml logs -f mikrotik-scraper-dev
    ;;

  "logs:prod")
    docker compose -f compose.prod.yaml logs -f mikrotik-scraper-prod
    ;;

  "check:pre-commit")
    echo "Running all pre-commit checks..."
    docker compose -f compose.dev.yaml exec mikrotik-scraper-dev pre-commit run --all-files
    ;;

  "help"|"")
    echo "Available commands:"
    echo ""
    echo "Development:"
    echo "  dev:start        - Start development container"
    echo "  dev:stop         - Stop development container"
    echo "  dev:rebuild      - Rebuild development image"
    echo "  dev:bash         - Access development shell"
    echo ""
    echo "Production:"
    echo "  prod:start       - Start production container"
    echo "  prod:stop        - Stop production container"
    echo ""
    echo "Code Quality:"
    echo "  test             - Run tests"
    echo "  lint             - Run linters"
    echo "  format           - Format code (black, isort)"
    echo "  check:pre-commit - Run all pre-commit checks"
    echo ""
    echo "Git:"
    echo "  commit           - Interactive commit with cz"
    echo ""
    echo "Inventory:"
    echo "  run:inventory    - Run inventory collection with config.yaml"
    echo ""
    echo "Logs:"
    echo "  logs:dev         - Development logs"
    echo "  logs:prod        - Production logs"
    echo ""
    echo "Usage: bash scripts/commands.sh [comando]"
    ;;

  *)
    echo "Unknown command: $1"
    echo "Run 'bash scripts/commands.sh help' for available commands"
    exit 1
    ;;
esac

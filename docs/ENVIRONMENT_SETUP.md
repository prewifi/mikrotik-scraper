# Development and Production Environment Guide

## Container Structure

The project is organized with two separate environments:

### Development (compose.dev.yaml)
```bash
docker-compose -f compose.dev.yaml up -d
docker-compose -f compose.dev.yaml exec ubiquiti-automation-dev bash
```

**Features:**
- Dockerfile.dev: Includes all development tools
- Complete volume mounted for hot-reload
- DEBUG level logging
- Pre-commit hooks enabled

### Production (compose.prod.yaml)
```bash
docker-compose -f compose.prod.yaml up -d
docker-compose -f compose.prod.yaml logs -f ubiquiti-automation-prod
```

**Features:**
- Dockerfile.prod: Optimized multi-stage build
- Minimal and secure image
- Read-only volume for configuration
- Health checks enabled
- Restart policy unless-stopped

## Commit Standards (Conventional Commits)

### Install pre-commit hooks

In the development container:
```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

### Supported Commit Types

```
feat(scope): Description - A new feature
fix(scope): Description - A bug fix
docs(scope): Description - Documentation
style(scope): Description - Formatting/Style
refactor(scope): Description - Code refactoring
perf(scope): Description - Performance improvements
test(scope): Description - Test added
chore(scope): Description - Build/dependency changes
ci(scope): Description - CI/CD changes
```

### Commit Examples

```bash
# Using commitizen (recommended)
cz commit

# Standard commit with hook validation
git commit -m "fix(mikrotik-client): resolve SSL connection timeout"
git commit -m "feat(analyzer): add performance analysis"
git commit -m "docs: update README with examples"
git commit -m "refactor(models): restructure data models"
git commit -m "test: add tests for connection pool"
```

## Separate Requirements

### requirements.txt (Production)
Minimal dependencies for production:
- routeros-api
- pydantic
- pyyaml
- python-dotenv
- rich
- python-json-logger

### requirements-dev.txt (Development)
Extends requirements.txt adding:
- Testing: pytest, pytest-cov, pytest-mock
- Formatting: black, isort
- Linting: flake8, mypy, bandit
- Git hooks: pre-commit, commitizen
- Debugging: ipython, pudb

## Development Flow

### 1. Clone and initial setup
```bash
git clone <repository>
cd ubiquiti-automation
docker-compose -f compose.dev.yaml build
docker-compose -f compose.dev.yaml up -d ubiquiti-automation-dev
```

### 2. Install pre-commit hooks
```bash
docker-compose -f compose.dev.yaml exec ubiquiti-automation-dev bash
pre-commit install
pre-commit install --hook-type commit-msg
exit
```

### 3. Develop and test
```bash
docker-compose -f compose.dev.yaml exec ubiquiti-automation-dev bash
# Inside the container
pytest
black src/
isort src/
flake8 src/
mypy src/
```

### 4. Commit with standard
```bash
# Inside container or on host machine
git add .
cz commit  # Or git commit -m "type(scope): message"
git push origin main
```

## Production Deployment

### Build and push image
```bash
docker build -t myregistry/ubiquiti-automation:1.0.0 -f Dockerfile.prod .
docker push myregistry/ubiquiti-automation:1.0.0
```

### Deploy
```bash
docker-compose -f compose.prod.yaml pull
docker-compose -f compose.prod.yaml up -d
docker-compose -f compose.prod.yaml logs -f
```

## Quality Checks

### Automatic pre-commit hooks
Each commit will automatically run:
- Message validation (Conventional Commits)
- Formatting (black, isort)
- Linting (flake8)
- Type checking (mypy)
- Security check (bandit)
- YAML validation

### Temporarily disable hooks
```bash
git commit --no-verify
```

## Troubleshooting

### Pre-commit hook not working
```bash
pre-commit run --all-files
pre-commit install-hooks
```

### Commitizen doesn't recognize messages
```bash
cz commit  # Use the interactive tool
```

### Container dependency issues
```bash
docker-compose -f compose.dev.yaml exec ubiquiti-automation-dev pip list
docker-compose -f compose.dev.yaml exec ubiquiti-automation-dev pip install --upgrade pip
```

## Important Notes

1. **Production has no pre-commit hooks** - Uses CI/CD validation
2. **Development volume is complete** - Real-time changes
3. **Production is read-only** - Separate config volume
4. **Health checks** - Automatic monitoring in production
5. **Separate logs** - Development on stdout, production in volume

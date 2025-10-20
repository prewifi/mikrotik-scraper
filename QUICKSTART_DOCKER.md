# 🚀 Guida Rapida - Development vs Production

## Riassunto della Struttura

Questa guida rapida riassume la configurazione di **development** e **production** del progetto.

```
ubiquiti-automation/
├── Dockerfile.dev         # Development (con tutti gli strumenti)
├── Dockerfile.prod        # Production (multi-stage, ottimizzato)
├── compose.dev.yaml       # Dev environment
├── compose.prod.yaml      # Prod environment
├── requirements.txt       # Dipendenze production
├── requirements-dev.txt   # Dipendenze dev (estende requirements.txt)
├── .pre-commit-config.yaml# Git hooks configuration
├── pyproject.toml         # Python project config + Commitizen
├── .bandit                # Security linter config
├── scripts/               # Helper scripts
│   ├── setup-dev.sh       # Setup environment
│   ├── deploy-prod.sh     # Production deployment
│   └── commands.sh        # Common commands
└── docs/
    └── ENVIRONMENT_SETUP.md  # Documentazione completa
```

## ⚡ Quick Start Development

```bash
# 1️⃣ Setup completo
bash scripts/setup-dev.sh

# 2️⃣ Accedi al container
docker-compose -f compose.dev.yaml exec ubiquiti-automation-dev bash

# 3️⃣ Dentro il container:
pytest                    # Run tests
black src/               # Format code
cz commit                # Commit con standard
```

## 🐳 Comandi Rapidi

```bash
# Development
bash scripts/commands.sh dev:start       # Avvia container dev
bash scripts/commands.sh dev:bash        # Accedi a bash
bash scripts/commands.sh test            # Run tests
bash scripts/commands.sh format          # Format code
bash scripts/commands.sh lint            # Run linters
bash scripts/commands.sh commit          # Interactive commit

# Production
bash scripts/commands.sh prod:start      # Avvia production
bash scripts/commands.sh prod:stop       # Ferma production

# Logs
bash scripts/commands.sh logs:dev        # Dev logs
bash scripts/commands.sh logs:prod       # Prod logs
```

## 📝 Standard di Commit (Conventional Commits)

```bash
# Formato: tipo(scope): descrizione

# Esempi:
git commit -m "feat(client): aggiungi connection pooling"
git commit -m "fix(analyzer): risolvi crash offline device"
git commit -m "docs: aggiorna README"
git commit -m "refactor(models): semplifica schema"
git commit -m "test(client): aggiungi test timeout"
git commit -m "chore: aggiorna dipendenze"
```

### Tipi Supportati
- `feat` - Nuova feature
- `fix` - Bug fix
- `docs` - Documentazione
- `style` - Formattazione
- `refactor` - Refactoring
- `perf` - Performance
- `test` - Test
- `chore` - Manutenzione
- `ci` - CI/CD

**Pre-commit hooks valideranno il formato automaticamente!**

## 🔧 Differenze Dev vs Prod

| Aspetto | Development | Production |
|---------|-------------|-----------|
| Dockerfile | `Dockerfile.dev` | `Dockerfile.prod` |
| Compose | `compose.dev.yaml` | `compose.prod.yaml` |
| Immagine | Include tutti gli strumenti | Multi-stage, minimale |
| Volume | Completo (hot-reload) | Read-only config |
| Dipendenze | requirements-dev.txt | requirements.txt |
| Log Level | DEBUG | INFO |
| Pre-commit | ✅ Abilitato | ❌ No (in CI/CD) |
| Health Check | ❌ No | ✅ Sì |

## 📦 Requirements Separati

### production: `requirements.txt`
```
routeros-api
pydantic
pyyaml
python-dotenv
rich
python-json-logger
```

### development: `requirements-dev.txt`
Estende `requirements.txt` con:
- Testing: pytest, pytest-cov, pytest-mock
- Formatting: black, isort
- Linting: flake8, mypy, bandit
- Commit: pre-commit, commitizen
- Debugging: ipython, pudb

## ✅ Pre-commit Hooks

Questi controlli eseguono **automaticamente** prima di ogni commit:

```bash
✓ Validazione Conventional Commits
✓ Formattazione (black, isort)
✓ Linting (flake8)
✓ Type checking (mypy)
✓ Security (bandit)
✓ YAML validation
✓ Trailing whitespace
✓ Large files check
```

### Setup (uno volta sola)
```bash
docker-compose -f compose.dev.yaml exec ubiquiti-automation-dev bash
pre-commit install
pre-commit install --hook-type commit-msg
```

### Disabilita temporaneamente
```bash
git commit --no-verify
```

## 🚀 Deploy Production

```bash
# 1. Costruisci immagine
bash scripts/deploy-prod.sh v1.0.0

# 2. Push (se richiesto)
docker push your-registry/ubiquiti-automation:v1.0.0

# 3. Deploy
docker-compose -f compose.prod.yaml pull
docker-compose -f compose.prod.yaml up -d

# 4. Verifica
docker-compose -f compose.prod.yaml logs -f
docker-compose -f compose.prod.yaml ps
```

## 🐛 Troubleshooting

### Pre-commit non funziona
```bash
docker-compose -f compose.dev.yaml exec ubiquiti-automation-dev bash
pre-commit run --all-files
```

### Dipendenze non trovate
```bash
docker-compose -f compose.dev.yaml exec ubiquiti-automation-dev bash
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Container non avvia
```bash
docker-compose -f compose.dev.yaml logs ubiquiti-automation-dev
docker-compose -f compose.dev.yaml build --no-cache
```

## 📚 Documentazione Completa

Per una guida più dettagliata, vedi:
- [docs/ENVIRONMENT_SETUP.md](./docs/ENVIRONMENT_SETUP.md) - Setup completo
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Linee guida di contribuzione
- [pyproject.toml](./pyproject.toml) - Configurazione Python

## 🎯 Workflow Tipico

```bash
# 1. Start dev
bash scripts/commands.sh dev:start

# 2. Work on code
docker-compose -f compose.dev.yaml exec ubiquiti-automation-dev bash
# ... edit files ...

# 3. Test & format
bash scripts/commands.sh test
bash scripts/commands.sh format

# 4. Commit (con pre-commit hooks)
bash scripts/commands.sh commit

# 5. Push
git push origin feature-branch

# 6. Create PR
# ... via GitHub interface ...
```

---

**💡 Tip:** Salva questo file nei tuoi bookmark! È la tua guida di riferimento rapido.

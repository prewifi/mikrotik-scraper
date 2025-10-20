# 📋 Commit Examples - Conventional Commits

This guide shows real examples of commits in the Conventional Commits format used in the project.

## Base Format

```
type(scope): short description

optional body explaining why and what

optional footer with issue references
```

---

## Common Examples

### 🎉 Feature Commit

```bash
git commit -m "feat(client): add connection pooling for MikroTik API"
```

Full body:
```
feat(client): add connection pooling for MikroTik API

Implements a connection pool to improve performance during
multiple operations on MikroTik devices.

- Maximum 10 concurrent connections
- 30 second timeout for idle connections
- Automatic retry with exponential backoff

Closes #42
```

### 🐛 Bug Fix

```bash
git commit -m "fix(analyzer): resolve crash when device offline"
```

Full body:
```
fix(analyzer): resolve crash when device offline

Adds proper error handling when a device goes offline
during analysis. Previously caused an unhandled KeyError.

- Added try/except around device lookup
- Logging of offline device
- Test case added for offline scenario

Fixes #38
```

### 📝 Documentation

```bash
git commit -m "docs: update installation guide with Docker"
```

Or with scope:
```bash
git commit -m "docs(readme): add API usage examples"
```

### 🎨 Style Changes

```bash
git commit -m "style(models): normalize import statement"
```

Body:
```
style(models): normalize import statement

Apply consistency to imports using isort:
- Ordered import statements
- Removed unused imports

Non-functional change.
```

### ♻️ Refactoring

```bash
git commit -m "refactor(analyzer): extract common logic in utility"
```

Body:
```
refactor(analyzer): extract common logic in utility

Extract repeated device validation logic into a separate
utility function to improve maintainability.

- Create utils.validate_device()
- Update analyzer.py and inventory.py
- Add test cases

Test coverage: 95%
```

### ⚡ Performance Improvement

```bash
git commit -m "perf(inventory): caching device results"
```

Body:
```
perf(inventory): implement device results caching

Add in-memory caching of device results to reduce
duplicate API calls during sequential analysis.

Benchmark results:
- Before: 1000 devices in 45s
- After: 1000 devices in 12s (3.75x speedup)

Cache timeout: 5 minutes
```

### ✅ Test Commit

```bash
git commit -m "test(client): add timeout handling tests"
```

Body:
```
test(client): add timeout handling tests

Add comprehensive test coverage for timeout scenarios:
- Connection timeout
- Read timeout
- Retry behavior

Coverage: 92%
```

### 🔧 Chore/Maintenance

```bash
git commit -m "chore: update dependencies (urllib3 2.0.0)"
```

Body:
```
chore: update dependencies

Updates:
- urllib3: 1.26.0 → 2.0.0
- pytest: 7.1.0 → 7.3.0
- pydantic: 1.9.0 → 2.0.0

BREAKING: Requires Python 3.9+
```

### 🔄 CI/CD Commit

```bash
git commit -m "ci: add GitHub Actions workflow"
```

Body:
```
ci: add GitHub Actions for test automation

Implement CI/CD pipeline that:
- Run pytest on every push
- Check code coverage
- Linting with flake8
- Type check with mypy

Runs on: Python 3.9, 3.10, 3.11, 3.12
```

---

## 🚀 Commit Rules

### ✅ DO

```bash
# ✅ Concise and descriptive
git commit -m "fix(client): exponential backoff retry handling"

# ✅ With scope
git commit -m "feat(analyzer): new JSON report format"

# ✅ Detailed with body
git commit -m "refactor(models): restructure Device class

- Add validation
- Improve type hints
- Add docstrings"

# ✅ With issue reference
git commit -m "fix(client): resolve SSL cert validation

Fixes #123"
```

### ❌ DON'T

```bash
# ❌ Vague and non-specific
git commit -m "fix stuff"
git commit -m "update code"

# ❌ Without type
git commit -m "new feature for connection pooling"

# ❌ Generic
git commit -m "fix(general): everything works now"

# ❌ Too long (max 50 char)
git commit -m "fix(client): this is a very long message that describes what was done in great detail"

# ❌ Mixed scope and type
git commit -m "analyzer fix: problems with offline devices"
```

---

## 📊 Commit Statistics

With Conventional Commits we can generate automatic statistics:

```bash
# Count feature commits
git log --oneline | grep "^feat" | wc -l

# Count bug fixes
git log --oneline | grep "^fix" | wc -l

# Automatic changelog (with commitizen)
cz bump --dry-run
```

---

## 🔗 Integrations

### Closing Issues

```bash
# Close issue #123
git commit -m "fix(client): resolve timeout

Fixes #123"

# Close multiple issues
git commit -m "fix(client): update error handling

Fixes #123, #124, #125"
```

### Cross-references

```bash
git commit -m "feat(analyzer): add performance metrics

Related to #100, #101"
```

### Breaking Changes

```bash
git commit -m "refactor!: change configuration API

BREAKING CHANGE: Configuration format changed from .yaml to .json"
```

---

## 🤖 Commitizen Interactive

When you run `cz commit`, you'll find an interactive prompt:

```
? Select the type of change: (Use arrow keys)
❯ feat      A new feature
  fix       A bug fix
  docs      Documentation only changes
  style     Changes that don't affect code meaning
  refactor  A code change that refactors
  perf      A code change that improves performance
  test      Adding missing tests

? What is the scope of this change? (leave empty if none)
client

? What is the subject of the change?
Add connection pooling support

? What is the body of the change? (leave empty if none)
Implements connection pool with configurable pool size and timeout.
Improves performance during multi-device operations.

? Is this a BREAKING CHANGE?
No

? Does this affect any OPEN issues?
Fixes #42
```

Result:
```
feat(client): Add connection pooling support

Implements connection pool with configurable pool size and timeout.
Improves performance during multi-device operations.

Fixes #42
```

---

## 📚 References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Angular Contributing Guide](https://github.com/angular/angular/blob/master/CONTRIBUTING.md)
- [Commitizen](http://commitizen.github.io/cz-cli/)

---

## Tips & Tricks

### Amend last commit
```bash
git commit --amend -m "fix(client): corrected message"
```

### Amend without changing message
```bash
git commit --amend --no-edit
```

### Interactive rebase
```bash
git rebase -i HEAD~3
```

### Soft reset (keep changes)
```bash
git reset --soft HEAD~1
```

---

**Remember:** Pre-commit hooks will validate the format! 🚀

### 🐛 Bug Fix

```bash
git commit -m "fix(analyzer): risolvi crash quando device offline"
```

Corpo completo:
```
fix(analyzer): risolvi crash quando device offline

Aggiunge proper error handling quando un dispositivo va offline
durante l'analisi. Prima causava un KeyError non gestito.

- Aggiunto try/except intorno a device lookup
- Logging di device offline
- Test case added per offline scenario

Fixes #38
```

### 📝 Documentation

```bash
git commit -m "docs: aggiorna guida installation con Docker"
```

O con scope:
```bash
git commit -m "docs(readme): aggiungi examples di utilizzo API"
```

### 🎨 Style Changes

```bash
git commit -m "style(models): normalizza import statement"
```

Corpo:
```
style(models): normalizza import statement

Applica consistenza ai import usando isort:
- Ordered import statements
- Removed unused imports

Non-functional change.
```

### ♻️ Refactoring

```bash
git commit -m "refactor(analyzer): extract common logic in utility"
```

Body:
```
refactor(analyzer): extract common logic in utility

Extracts the device validation logic repeated in a separate
utility function to improve maintainability.

- Create utils.validate_device()
- Update analyzer.py and inventory.py
- Add test cases

Test coverage: 95%
```

### ⚡ Performance Improvement

```bash
git commit -m "perf(inventory): implement device results caching"
```

Body:
```
perf(inventory): implement device results caching

Adds in-memory caching of device results to reduce
duplicate API calls during sequential analysis.

Benchmark results:
- Before: 1000 devices in 45s
- After: 1000 devices in 12s (3.75x speedup)

Cache timeout: 5 minutes
```

### ✅ Test Commit

```bash
git commit -m "test(client): add tests for timeout handling"
```

Corpo:
```
test(client): aggiungi test per timeout handling

Aggiunge comprehensive test coverage per timeout scenarios:
- Connection timeout
- Read timeout
- Retry behavior

Coverage: 92%
```

### 🔧 Chore/Maintenance

```bash
git commit -m "chore: aggiorna dipendenze (urllib3 2.0.0)"
```

Corpo:
```
chore: aggiorna dipendenze

Updates:
- urllib3: 1.26.0 → 2.0.0
- pytest: 7.1.0 → 7.3.0
- pydantic: 1.9.0 → 2.0.0

BREAKING: Richiede Python 3.9+
```

### 🔄 CI/CD Commit

```bash
git commit -m "ci: aggiungi GitHub Actions workflow"
```

Corpo:
```
ci: aggiungi GitHub Actions per test automation

Implementa CI/CD pipeline che:
- Esegue pytest su ogni push
- Controlla code coverage
- Linting con flake8
- Type check con mypy

Runs on: Python 3.9, 3.10, 3.11, 3.12
```

---

## 🚀 Commit Rules

### ✅ DO

```bash
# ✅ Conciso e descritivo
git commit -m "fix(client): timeout handling con retry exponential"

# ✅ Con scope
git commit -m "feat(analyzer): nuovo report format JSON"

# ✅ Dettagliato con corpo
git commit -m "refactor(models): restructura Device class

- Aggiunge validation
- Migliora type hints
- Adds docstrings"

# ✅ Con riferimento a issue
git commit -m "fix(client): risolvi SSL cert validation

Fixes #123"
```

### ❌ DON'T

```bash
# ❌ Vago e non specifico
git commit -m "fix stuff"
git commit -m "update code"

# ❌ Senza tipo
git commit -m "nuovo feature per connection pooling"

# ❌ Generico
git commit -m "fix(general): everything works now"

# ❌ Troppo lungo (max 50 char)
git commit -m "fix(client): this is a very long message that describes what was done in great detail"

# ❌ Misto scope e tipo
git commit -m "analyzer fix: problemi con offline devices"
```

---

## 📊 Statistiche Commit

Con i Conventional Commits possiamo generare statistiche automatiche:

```bash
# Conta feature commit
git log --oneline | grep "^feat" | wc -l

# Conta bug fix
git log --oneline | grep "^fix" | wc -l

# Changelog automatico (con commitizen)
cz bump --dry-run
```

---

## 🔗 Integrazioni

### Closing Issues

```bash
# Chiude issue #123
git commit -m "fix(client): risolvi timeout

Fixes #123"

# Chiude multiple issue
git commit -m "fix(client): aggiorna error handling

Fixes #123, #124, #125"
```

### Cross-references

```bash
git commit -m "feat(analyzer): aggiungi performance metrics

Related to #100, #101"
```

### Breaking Changes

```bash
git commit -m "refactor!: cambia API di configuration

BREAKING CHANGE: Configuration format è cambiato da .yaml a .json"
```

---

## 🤖 Commitizen Interactive

Quando esegui `cz commit`, troverai un prompt interattivo:

```
? Select the type of change: (Use arrow keys)
❯ feat      Una nuova feature
  fix       Una correzione di bug
  docs      Solo modifiche alla documentazione
  style     Modifiche di stile (no logic change)
  refactor  Refactoring codice
  perf      Miglioramenti di performance
  test      Aggiunta di test mancanti

? What is the scope of this change? (leave empty if none)
client

? What is the subject of the change?
Add connection pooling support

? What is the body of the change? (leave empty if none)
Implements connection pool with configurable pool size and timeout.
Improves performance during multi-device operations.

? Is this a BREAKING CHANGE?
No

? Does this affect any OPEN issues?
Fixes #42
```

Risultato:
```
feat(client): Add connection pooling support

Implements connection pool with configurable pool size and timeout.
Improves performance during multi-device operations.

Fixes #42
```

---

## 📚 References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Angular Contributing Guide](https://github.com/angular/angular/blob/master/CONTRIBUTING.md)
- [Commitizen](http://commitizen.github.io/cz-cli/)

---

## Tips & Tricks

### Amend last commit
```bash
git commit --amend -m "fix(client): corrected message"
```

### Amend without changing message
```bash
git commit --amend --no-edit
```

### Interactive rebase
```bash
git rebase -i HEAD~3
```

### Soft reset (keep changes)
```bash
git reset --soft HEAD~1
```

---

**Remember:** Pre-commit hooks will validate the format! 🚀

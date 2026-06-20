# Contributing

Thanks for your interest in this project.

## Development setup

```bash
git clone https://github.com/bonsteeve/embedded-dispenser.git
cd embedded-dispenser
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Workflow

1. Branch from `main` using `feature/` or `fix/` prefixes.
2. Add or update tests for behavioral changes.
3. Run `pytest -v` and `ruff check src tests examples` locally.
4. Open a pull request with a clear summary and test plan.

## Commit style

Use conventional prefixes where practical: `feat:`, `fix:`, `docs:`, `chore:`, `test:`.
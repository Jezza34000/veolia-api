# Contributing

Thank you for considering contributing to `veolia-api`! All contributions are welcome: bug reports, portal additions, feature suggestions, and code improvements.

## Table of contents

- [Reporting a bug](#reporting-a-bug)
- [Suggesting a feature](#suggesting-a-feature)
- [Adding a portal](#adding-a-portal)
- [Development setup](#development-setup)
- [Submitting a pull request](#submitting-a-pull-request)
- [Code style](#code-style)

---

## Reporting a bug

1. Search [existing issues](https://github.com/Jezza34000/veolia-api/issues) to avoid duplicates.
2. Open a new issue and include:
   - Python version and OS
   - `veolia-api` version (`pip show veolia-api`)
   - Minimal reproduction steps
   - Full traceback if applicable

## Suggesting a feature

Open an issue with the `enhancement` label. Describe the use case and why it would benefit other users.

---

## Adding a portal

This is the most common contribution. The only file to edit is **`veolia_api/portals.py`**:

```python
VEOLIA_PORTAL_CLIENTS: dict[str, str] = {
    "eau.veolia.fr": "3kghade1fg54739kj8pkbova8j",
    "eaudetm.monespace.eau.veolia.fr": "19bjc8ldefie683n889iiubjc8",
    "your-portal.veolia.fr": "your-cognito-client-id",  # <-- add here
}
```

Also update the **Supported portals** table in `README.md`.

### How to find your client ID

1. Open your Veolia portal login page in a browser
2. Open the developer tools (F12) > **Network** tab
3. Attempt to log in
4. Look for a request to `cognito-idp.eu-west-3.amazonaws.com` — the `client_id` field in the request body is the value you need

---

## Development setup

**With devbox** (recommended — no Python install required):

```bash
devbox shell
```

**With an existing Python environment** (Python 3.11+):

```bash
pip install -r requirements.txt
pre-commit install
```

---

## Submitting a pull request

1. [Fork](https://github.com/Jezza34000/veolia-api/fork) the repository
2. Create a branch from `main`: `git checkout -b my-change`
3. Make your changes
4. Run the checks: `pre-commit run --all-files`
5. Push your branch and open a pull request against `main`
6. Fill in the pull request template and describe what your change does

All checks must pass before a PR can be merged.

---

## Code style

This project uses:

- [black](https://github.com/psf/black) for formatting
- [ruff](https://github.com/astral-sh/ruff) for linting
- [codespell](https://github.com/codespell-project/codespell) for typos
- [gitleaks](https://github.com/gitleaks/gitleaks) to prevent secret leaks

Run all checks at once:

```bash
pre-commit run --all-files
```

Hooks run automatically on every commit once `pre-commit install` has been run.

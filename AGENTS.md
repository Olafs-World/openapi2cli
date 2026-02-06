# AGENTS.md

Instructions for AI agents working on this repository.

## Overview

**openapi2cli** generates CLI tools from OpenAPI 3.x specs. Built for AI agents who need to interact with APIs.

## Development

### Setup

```bash
git clone https://github.com/Olafs-World/openapi2cli.git
cd openapi2cli
uv sync
```

### Running Tests

```bash
uv run pytest
uv run ruff check .
```

### Testing Locally

```bash
uv run openapi2cli generate https://httpbin.org/spec.json --name httpbin
python httpbin_cli.py --help
```

## Project Structure

```
openapi2cli/
├── __init__.py      # Package exports
├── cli.py           # CLI entry point (argparse)
├── parser.py        # OpenAPI spec parsing
├── generator.py     # CLI code generation
├── runtime.py       # Runtime helpers for generated CLIs
tests/
├── test_cli.py      # CLI tests
├── test_parser.py   # Parser tests
├── test_generator.py # Generator tests
├── test_runtime.py  # Runtime tests
├── test_e2e.py      # End-to-end tests
```

## Making a Release

**⚠️ NEVER manually publish to PyPI!** Always use git tags - CI handles PyPI automatically.

### Release Process

1. **Bump version** in `pyproject.toml`
2. **Update CHANGELOG.md** with changes under new version header
3. **Commit**: `git add -A && git commit -m "Bump version to X.Y.Z"`
4. **Tag**: `git tag vX.Y.Z`
5. **Push both**: `git push && git push --tags`

CI will automatically:
- Run tests on Python 3.9-3.12
- Publish to PyPI (only on tag push)

6. **Create GitHub Release** (optional but recommended):
   - Go to Releases → Draft new release
   - Select the tag you just pushed
   - Copy release notes from CHANGELOG.md

### Why not manual PyPI publish?

- Keeps GitHub releases and PyPI versions in sync
- Ensures tests pass before publishing
- Creates audit trail via CI logs
- Prevents accidental publishes of broken code

## Code Style

- Use `ruff` for linting
- Follow existing patterns in the codebase
- Generated CLIs should be standalone (single file, minimal deps)
- Support common auth patterns (API key, Bearer, Basic)

## Architecture

1. **Parser** - Reads OpenAPI spec, extracts endpoints/params
2. **Generator** - Creates Python CLI code from parsed spec
3. **Runtime** - Helper functions used by generated CLIs

## Limitations to Address

- Only OpenAPI 3.x (not Swagger 2.0)
- No file upload support yet
- OAuth2 flows not fully implemented
- Complex nested request bodies need `--data` JSON flag

## Dependencies

- `pyyaml` - YAML parsing
- `requests` - HTTP client (for generated CLIs)
- `pytest` - Testing (dev)
- `ruff` - Linting (dev)

## Git Conventions

- Commit messages: imperative mood ("Add feature" not "Added feature")
- Co-author AI contributions: `Co-authored-by: olaf-s-app[bot] <259723076+olaf-s-app[bot]@users.noreply.github.com>`

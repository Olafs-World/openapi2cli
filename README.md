# openapi2cli 🔧

[![CI](https://github.com/Olafs-World/openapi2cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Olafs-World/openapi2cli/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/openapi2cli.svg)](https://pypi.org/project/openapi2cli/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Generate CLI tools from OpenAPI specs.** Built for AI agents who need to interact with APIs.

```bash
# Generate a CLI from any OpenAPI spec
$ openapi2cli generate https://httpbin.org/spec.json --name httpbin

# Use it immediately
$ ./httpbin_cli.py get --output json
{
  "url": "https://httpbin.org/get",
  "headers": { ... }
}
```

## Why?

AI agents are great at executing CLI commands. They're less great at crafting HTTP requests from memory. This tool bridges the gap:

1. **OpenAPI spec** → any API with a spec becomes usable
2. **CLI generation** → instant `--help`, tab completion, validation
3. **No code changes** → just point at a spec and go

## Installation

```bash
pip install openapi2cli
```

## Quick Start

### Generate a CLI

```bash
# From a URL
openapi2cli generate https://petstore3.swagger.io/api/v3/openapi.json --name petstore

# From a local file
openapi2cli generate ./api-spec.yaml --name myapi --output myapi
```

### Use the Generated CLI

```bash
# See available commands
./petstore --help

# List pets
./petstore pet find-by-status --status available

# Add a pet (with auth)
export PETSTORE_API_KEY=your-key
./petstore pet add --name "Fluffy" --status available

# JSON output for scripting
./petstore pet get --pet-id 123 --output json | jq '.name'
```

### Inspect a Spec

```bash
# See what's in a spec without generating
openapi2cli inspect https://httpbin.org/spec.json
```

## Features

| Feature | Description |
|---------|-------------|
| 🔍 **Auto-discovery** | Parses OpenAPI 3.x specs (YAML or JSON) |
| 🏷️ **Smart grouping** | Commands grouped by API tags |
| 🔐 **Auth support** | API keys, Bearer tokens, env vars |
| 📊 **Output formats** | JSON, table, or raw |
| ⚡ **Fast generation** | Single command, instant CLI |
| 🤖 **Agent-friendly** | Self-documenting with `--help` |

## Configuration

### Authentication

Generated CLIs support multiple auth methods:

```bash
# Via environment variable (recommended)
export PETSTORE_API_KEY=your-key
./petstore pet list

# Via CLI option
./petstore --api-key your-key pet list

# Bearer token
export PETSTORE_TOKEN=your-bearer-token
./petstore pet list
```

The env var prefix is derived from the CLI name (uppercase, underscores).

### Base URL Override

```bash
# Use a different API server
./petstore --base-url https://staging.petstore.io/api pet list
```

### Output Formats

```bash
# JSON (default, good for piping)
./petstore pet list --output json

# Table (human-readable, requires rich)
./petstore pet list --output table

# Raw (API response as-is)
./petstore pet list --output raw
```

## Generated CLI Structure

For a spec with tags `pet`, `store`, `user`:

```
petstore
├── pet
│   ├── add          # POST /pet
│   ├── get          # GET /pet/{petId}
│   ├── update       # PUT /pet
│   ├── delete       # DELETE /pet/{petId}
│   └── find-by-status
├── store
│   ├── order
│   └── inventory
└── user
    ├── create
    ├── login
    └── logout
```

## API Reference

### `openapi2cli generate`

```
openapi2cli generate SPEC --name NAME [--output PATH] [--stdout]

Arguments:
  SPEC          OpenAPI spec (file path or URL)

Options:
  -n, --name    CLI name (required)
  -o, --output  Output file path (default: {name}_cli.py)
  --stdout      Print to stdout instead of file
```

### `openapi2cli inspect`

```
openapi2cli inspect SPEC

Arguments:
  SPEC          OpenAPI spec (file path or URL)
```

### Python API

```python
from openapi2cli import OpenAPIParser, CLIGenerator

# Parse a spec
parser = OpenAPIParser()
spec = parser.parse("https://api.example.com/openapi.json")

print(f"API: {spec.title}")
print(f"Endpoints: {len(spec.endpoints)}")

# Generate CLI
generator = CLIGenerator()
cli = generator.generate(spec, name="example")

# Save to file
cli.save("example_cli.py")

# Or get the code
code = cli.to_python()
```

## Development

```bash
# Clone
git clone https://github.com/Olafs-World/openapi2cli.git
cd openapi2cli

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run only unit tests (no API calls)
pytest tests/ -v -m "not integration"
```

## How It Works

1. **Parse** - Load OpenAPI 3.x spec (YAML/JSON, local/URL)
2. **Extract** - Pull endpoints, parameters, auth schemes, request bodies
3. **Generate** - Create Click-based CLI with proper groups and options
4. **Output** - Save as standalone Python script (executable)

The generated CLI uses `requests` for HTTP and optionally `rich` for pretty output.

## Limitations

- OpenAPI 3.x only (not Swagger 2.0)
- No file upload support yet
- Complex nested request bodies may need `--data` JSON flag
- OAuth2 flows not fully implemented (use `--token` with pre-obtained tokens)

## License

MIT © [Olaf](https://olafs-world.vercel.app)

---

<p align="center">
  <i>Built by an AI who got tired of writing curl commands 🤖</i>
</p>

"""CLI code generator."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from jinja2 import Template

from .parser import AuthScheme, Endpoint, ParsedSpec


@dataclass
class CLIOption:
    """A CLI option/argument."""

    name: str
    param_type: str = "str"
    required: bool = False
    default: Optional[str] = None
    help: str = ""
    is_flag: bool = False
    multiple: bool = False
    location: str = "query"  # path, query, header, cookie, body, body_raw
    api_name: str = ""        # original API parameter/property name

    @property
    def help_literal(self) -> str:
        """Python string literal for Click help text."""
        return repr(self.help or "")

    @property
    def default_literal(self) -> str:
        """Python string literal for default value."""
        return repr(self.default)


@dataclass
class CLICommand:
    """A CLI command."""

    name: str
    method: str
    path: str
    help: str = ""
    options: List[CLIOption] = field(default_factory=list)
    has_body: bool = False


@dataclass
class CLIGroup:
    """A group of CLI commands (tag)."""

    name: str
    help: str = ""
    commands: List[CLICommand] = field(default_factory=list)


@dataclass
class GeneratedCLI:
    """A generated CLI structure."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    base_url: str = ""
    groups: List[CLIGroup] = field(default_factory=list)
    global_options: List[CLIOption] = field(default_factory=list)
    auth_schemes: List[AuthScheme] = field(default_factory=list)
    api_key_header_name: str = ""

    def to_python(self) -> str:
        """Generate Python code for the CLI."""
        return CLI_TEMPLATE.render(cli=self)

    def to_standalone_script(self) -> str:
        """Generate a standalone executable script."""
        code = self.to_python()
        return f"#!/usr/bin/env python3\n{code}"

    def save(self, path: Union[Path, str]) -> None:
        """Save the generated CLI to a file."""
        path = Path(path)
        code = self.to_standalone_script()
        path.write_text(code)
        # Make executable
        path.chmod(0o755)


class CLIGenerator:
    """Generates CLI code from a parsed OpenAPI spec."""

    def generate(self, spec: ParsedSpec, name: str) -> GeneratedCLI:
        """Generate a CLI from a parsed spec."""
        # Generate global options (auth, output format, base URL)
        global_options = self._generate_global_options(spec)

        # Group endpoints by tag and generate command groups
        grouped = spec.group_by_tag()
        groups = []

        for tag, endpoints in grouped.items():
            group = self._generate_group(tag, endpoints)
            groups.append(group)

        return GeneratedCLI(
            name=name,
            version=spec.version,
            description=self._clean_text(spec.description) or f"CLI for {self._clean_text(spec.title)}",
            base_url=spec.base_url,
            groups=groups,
            global_options=global_options,
            auth_schemes=spec.auth_schemes,
            api_key_header_name=self._api_key_header_name(spec.auth_schemes),
        )

    def _generate_global_options(self, spec: ParsedSpec) -> List[CLIOption]:
        """Generate global CLI options."""
        options = [
            CLIOption(
                name="--output",
                param_type="str",
                default="table",
                help="Output format (json, table, raw)",
            ),
            CLIOption(
                name="--base-url",
                param_type="str",
                default=spec.base_url,
                help="API base URL",
            ),
        ]

        # Add auth options based on security schemes
        for scheme in spec.auth_schemes:
            if scheme.type == "apiKey":
                options.append(CLIOption(
                    name="--api-key",
                    param_type="str",
                    help=f"API key ({scheme.param_name})",
                ))
            elif scheme.type == "http" and scheme.scheme == "bearer":
                options.append(CLIOption(
                    name="--token",
                    param_type="str",
                    help="Bearer token for authentication",
                ))

        # Default auth option if no schemes defined
        if not any(o.name in ("--api-key", "--token") for o in options):
            options.append(CLIOption(
                name="--api-key",
                param_type="str",
                help="API key for authentication",
            ))

        return options

    def _generate_group(self, tag: str, endpoints: List[Endpoint]) -> CLIGroup:
        """Generate a command group from a tag."""
        commands = []

        for endpoint in endpoints:
            cmd = self._generate_command(endpoint)
            commands.append(cmd)

        return CLIGroup(
            name=self._sanitize_name(tag),
            help=f"Commands for {self._clean_text(tag)}",
            commands=commands,
        )

    def _generate_command(self, endpoint: Endpoint) -> CLICommand:
        """Generate a CLI command from an endpoint."""
        options = []
        seen_names = set()

        def add_option(opt: CLIOption) -> None:
            """Add option if name not already used."""
            if opt.name not in seen_names:
                seen_names.add(opt.name)
                options.append(opt)

        # Add options for parameters
        for param in endpoint.parameters:
            add_option(CLIOption(
                name=param.cli_name,
                param_type=self._map_type(param.schema_type),
                required=param.required,
                default=str(param.default) if param.default is not None else None,
                help=self._clean_text(param.description) or f"{param.name} parameter",
                location=param.location,
                api_name=param.name,
            ))

        # Add options for request body properties
        has_body = False
        if endpoint.request_body:
            has_body = True
            for prop_name, prop_schema in endpoint.request_body.properties.items():
                required = prop_name in endpoint.request_body.required_props
                add_option(CLIOption(
                    name=f"--{self._sanitize_name(prop_name)}",
                    param_type=self._map_type(prop_schema.get('type', 'string')),
                    required=required,
                    help=self._clean_text(prop_schema.get('description', '')) or f"{prop_name} field",
                    location="body",
                    api_name=prop_name,
                ))

            # Also add a --data option for raw JSON input
            add_option(CLIOption(
                name="--data",
                param_type="str",
                help="Raw JSON data for request body",
                location="body_raw",
                api_name="data",
            ))

        return CLICommand(
            name=endpoint.cli_name,
            method=endpoint.method,
            path=endpoint.path,
            help=self._clean_text(endpoint.summary) or self._clean_text(endpoint.description) or f"{endpoint.method} {endpoint.path}",
            options=options,
            has_body=has_body,
        )

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use as a CLI command/option."""
        # Convert camelCase to kebab-case
        name = re.sub(r'([a-z])([A-Z])', r'\1-\2', name)
        # Replace underscores, spaces, dots with hyphens
        name = name.replace('_', '-').replace(' ', '-').replace('.', '-')
        # Remove invalid characters
        name = re.sub(r'[^a-zA-Z0-9-]', '', name)
        # Remove consecutive hyphens
        name = re.sub(r'-+', '-', name)
        # Remove leading/trailing hyphens
        name = name.strip('-')
        return name.lower()

    def _map_type(self, schema_type: str) -> str:
        """Map OpenAPI type to Python/Click type."""
        mapping = {
            'integer': 'int',
            'number': 'float',
            'boolean': 'bool',
            'array': 'str',  # JSON string for arrays
            'object': 'str',  # JSON string for objects
        }
        return mapping.get(schema_type, 'str')

    def _clean_text(self, text: str) -> str:
        """Normalize free-text fields so they are safe in generated source strings."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", str(text)).strip()

    def _api_key_header_name(self, auth_schemes: List[AuthScheme]) -> str:
        """Return the API key header name, if the spec defines one."""
        for scheme in auth_schemes:
            if scheme.type == "apiKey" and scheme.location == "header" and scheme.param_name:
                return scheme.param_name
        return ""


# Template for generated CLI - use raw strings to avoid escaping issues
CLI_TEMPLATE_STR = '''
"""{{ cli.name }} - Generated CLI for {{ cli.description }}

Auto-generated by openapi2cli. Do not edit manually.
"""

import json
import os
import sys
from typing import Optional

import click
import requests

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Configuration
BASE_URL = "{{ cli.base_url }}"
ENV_PREFIX = "{{ cli.name.upper().replace('-', '_') }}"


def get_auth_headers(api_key: Optional[str] = None, token: Optional[str] = None) -> dict:
    """Get authentication headers."""
    headers = {}

    # Try CLI args first, then env vars
    key = api_key or os.environ.get(ENV_PREFIX + "_API_KEY")
    tok = token or os.environ.get(ENV_PREFIX + "_TOKEN")

    if tok:
        headers["Authorization"] = "Bearer " + tok
    elif key:
        {%- if cli.api_key_header_name %}
        headers["{{ cli.api_key_header_name }}"] = key
        {%- else %}
        headers["X-API-Key"] = key
        {%- endif %}

    return headers


def format_output(data, output_format: str):
    """Format output based on requested format."""
    if output_format == "json":
        click.echo(json.dumps(data, indent=2))
    elif output_format == "raw":
        click.echo(data)
    elif output_format == "table" and RICH_AVAILABLE:
        console = Console()
        if isinstance(data, list) and data:
            table = Table()
            first = data[0]
            if isinstance(first, dict):
                for key in first.keys():
                    table.add_column(str(key))
                for item in data:
                    if isinstance(item, dict):
                        table.add_row(*[str(v) for v in item.values()])
            else:
                table.add_column("value")
                for item in data:
                    table.add_row(str(item))
            console.print(table)
        elif isinstance(data, dict):
            table = Table()
            table.add_column("Key")
            table.add_column("Value")
            for k, v in data.items():
                table.add_row(str(k), str(v))
            console.print(table)
        else:
            console.print(data)
    else:
        click.echo(json.dumps(data, indent=2))


def make_request(
    method: str,
    path: str,
    base_url: str,
    params: dict = None,
    json_data: dict = None,
    headers: dict = None,
    path_params: dict = None,
):
    """Make an HTTP request to the API."""
    if path_params:
        for key, value in path_params.items():
            path = path.replace("{" + key + "}", str(value))

    url = base_url.rstrip("/") + path

    try:
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    except requests.exceptions.RequestException as e:
        click.echo("Error: " + str(e), err=True)
        sys.exit(1)


@click.group()
@click.option("--output", "-o", default="json", help="Output format (json, table, raw)")
@click.option("--base-url", default=BASE_URL, help="API base URL")
@click.option("--api-key", envvar=ENV_PREFIX + "_API_KEY", help="API key")
@click.option("--token", envvar=ENV_PREFIX + "_TOKEN", help="Bearer token")
@click.version_option(version="{{ cli.version }}")
@click.pass_context
def cli(ctx, output, base_url, api_key, token):
    """{{ cli.description }}"""
    ctx.ensure_object(dict)
    ctx.obj["output"] = output
    ctx.obj["base_url"] = base_url
    ctx.obj["headers"] = get_auth_headers(api_key, token)

{% for group in cli.groups %}

@cli.group()
def {{ group.name | replace("-", "_") }}():
    """{{ group.help }}"""
    pass

{% for cmd in group.commands %}

@{{ group.name | replace("-", "_") }}.command("{{ cmd.name }}")
{%- for opt in cmd.options %}
@click.option("{{ opt.name }}"{% if opt.required %}, required=True{% endif %}{% if opt.default is not none %}, default={{ opt.default_literal }}{% endif %}, help={{ opt.help_literal }})
{%- endfor %}
@click.pass_context
def {{ group.name | replace("-", "_") | replace(".", "_") }}_{{ cmd.name | replace("-", "_") | replace(".", "_") }}(ctx{% for opt in cmd.options %}, {{ opt.name | replace("--", "") | replace("-", "_") | replace(".", "_") }}{% endfor %}):
    """{{ cmd.help | replace('"', '\\"') }}"""
    path_params = {}
    query_params = {}
    body_data = {}

    {%- for opt in cmd.options %}
    {%- set var_name = opt.name | replace("--", "") | replace("-", "_") %}
    if {{ var_name }} is not None:
        {%- if opt.location == "path" %}
        path_params["{{ opt.api_name }}"] = {{ var_name }}
        {%- elif opt.location == "body_raw" %}
        body_data = json.loads({{ var_name }})
        {%- elif opt.location == "body" %}
        body_data["{{ opt.api_name }}"] = {{ var_name }}
        {%- else %}
        query_params["{{ opt.api_name }}"] = {{ var_name }}
        {%- endif %}
    {%- endfor %}

    result = make_request(
        method="{{ cmd.method }}",
        path="{{ cmd.path }}",
        base_url=ctx.obj["base_url"],
        params=query_params or None,
        json_data=body_data or None,
        headers=ctx.obj["headers"],
        path_params=path_params or None,
    )

    format_output(result, ctx.obj["output"])
{% endfor %}
{% endfor %}


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
'''

CLI_TEMPLATE = Template(CLI_TEMPLATE_STR)

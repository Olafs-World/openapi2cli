"""Main CLI for openapi2cli."""

import sys
from pathlib import Path

import click

from . import __version__
from .generator import CLIGenerator
from .parser import OpenAPIParser


@click.group()
@click.version_option(version=__version__)
def main():
    """openapi2cli - Generate CLI tools from OpenAPI specs.

    Built for AI agents who need to interact with APIs.

    Example:

        # Generate a CLI from a spec
        openapi2cli generate https://httpbin.org/spec.json --name httpbin

        # Then use it
        ./httpbin get --output json
    """
    pass


@main.command()
@click.argument("spec", type=str)
@click.option("--name", "-n", required=True, help="Name for the generated CLI")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--stdout", is_flag=True, help="Print to stdout instead of file")
def generate(spec: str, name: str, output: str, stdout: bool):
    """Generate a CLI from an OpenAPI spec.

    SPEC can be a file path or URL to an OpenAPI 3.x specification.

    Examples:

        openapi2cli generate petstore.yaml --name petstore
        openapi2cli generate https://api.example.com/openapi.json --name example -o example_cli.py
    """
    try:
        # Parse the spec
        parser = OpenAPIParser()
        parsed = parser.parse(spec)

        click.echo(f"Parsed: {parsed.title} v{parsed.version}", err=True)
        click.echo(f"Found {len(parsed.endpoints)} endpoints", err=True)

        # Generate CLI
        generator = CLIGenerator()
        cli = generator.generate(parsed, name=name)

        click.echo(f"Generated {len(cli.groups)} command groups", err=True)

        # Output
        if stdout:
            click.echo(cli.to_python())
        else:
            output_path = Path(output) if output else Path(f"{name}_cli.py")
            cli.save(output_path)
            click.echo(f"Saved to: {output_path}", err=True)
            click.echo(f"\nUsage: python {output_path} --help", err=True)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("spec", type=str)
def inspect(spec: str):
    """Inspect an OpenAPI spec without generating code.

    Shows the structure of the API: endpoints, parameters, auth, etc.
    """
    try:
        parser = OpenAPIParser()
        parsed = parser.parse(spec)

        click.echo(f"\n📋 {parsed.title} v{parsed.version}")
        click.echo(f"   {parsed.description[:100]}..." if len(parsed.description) > 100 else f"   {parsed.description}")
        click.echo(f"\n🌐 Base URL: {parsed.base_url}")

        # Auth schemes
        if parsed.auth_schemes:
            click.echo("\n🔐 Authentication:")
            for scheme in parsed.auth_schemes:
                click.echo(f"   - {scheme.name}: {scheme.type}")

        # Endpoints by tag
        grouped = parsed.group_by_tag()
        click.echo(f"\n📡 Endpoints ({len(parsed.endpoints)} total):")

        for tag, endpoints in sorted(grouped.items()):
            click.echo(f"\n   [{tag}]")
            for ep in endpoints[:5]:  # Show first 5
                params = ", ".join(p.name for p in ep.parameters[:3])
                if len(ep.parameters) > 3:
                    params += "..."
                click.echo(f"   • {ep.method:6} {ep.path}")
                if params:
                    click.echo(f"           params: {params}")
            if len(endpoints) > 5:
                click.echo(f"   ... and {len(endpoints) - 5} more")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

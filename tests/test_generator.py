"""Tests for CLI code generation."""

from pathlib import Path

from openapi2cli.generator import CLIGenerator, GeneratedCLI
from openapi2cli.parser import OpenAPIParser

FIXTURES = Path(__file__).parent / "fixtures"


class TestCLIGenerator:
    """Tests for the CLI generator."""

    def test_generates_cli_structure(self):
        """Generates a CLI with command groups."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        assert isinstance(cli, GeneratedCLI)
        assert cli.name == "petstore"
        assert len(cli.groups) > 0

    def test_generates_group_for_each_tag(self):
        """Creates a command group for each tag."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        group_names = [g.name for g in cli.groups]
        assert "pet" in group_names
        assert "store" in group_names
        assert "user" in group_names

    def test_generates_commands_for_endpoints(self):
        """Creates commands for each endpoint."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        pet_group = next(g for g in cli.groups if g.name == "pet")
        command_names = [c.name for c in pet_group.commands]

        # Should have commands for pet operations
        assert len(command_names) > 0
        # e.g., "add", "get", "update", "delete", "find-by-status"
        assert any("get" in name or "find" in name for name in command_names)

    def test_generates_options_for_parameters(self):
        """Creates CLI options for endpoint parameters."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        pet_group = next(g for g in cli.groups if g.name == "pet")

        # Find a command with parameters (e.g., get pet by ID)
        get_cmd = next(
            (c for c in pet_group.commands if "get" in c.name or "by-id" in c.name),
            None
        )

        if get_cmd:
            # Should have --pet-id or similar option
            option_names = [o.name for o in get_cmd.options]
            assert len(option_names) > 0

    def test_generates_options_for_request_body(self):
        """Creates CLI options for request body fields."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        pet_group = next(g for g in cli.groups if g.name == "pet")

        # Find POST command (add pet)
        add_cmd = next(
            (c for c in pet_group.commands if c.method == "POST"),
            None
        )

        if add_cmd:
            option_names = [o.name for o in add_cmd.options]
            # Pet has name, photoUrls, etc.
            assert "--name" in option_names or "--data" in option_names

    def test_generates_auth_options(self):
        """Generates authentication options."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        # Should have global auth options
        global_options = [o.name for o in cli.global_options]
        assert "--api-key" in global_options or "--token" in global_options

    def test_generates_output_format_option(self):
        """Generates --output option for format selection."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        global_options = [o.name for o in cli.global_options]
        assert "--output" in global_options or "-o" in global_options

    def test_exports_to_python_file(self):
        """Can export CLI to a Python file."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        code = cli.to_python()

        assert "import click" in code or "import typer" in code
        assert "def pet" in code or "pet =" in code
        assert "def main" in code or "@app.command" in code

    def test_generated_code_is_valid_python(self):
        """Generated code can be compiled."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        code = cli.to_python()

        # Should compile without syntax errors
        compile(code, "<generated>", "exec")


class TestGeneratedCLI:
    """Tests for the GeneratedCLI data class."""

    def test_to_standalone_script(self):
        """Can export as standalone executable script."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        script = cli.to_standalone_script()

        assert script.startswith("#!/usr/bin/env python3")
        assert "if __name__" in script

    def test_save_to_file(self, tmp_path):
        """Can save generated CLI to a file."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="petstore")

        output_path = tmp_path / "petstore_cli.py"
        cli.save(output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "click" in content or "typer" in content

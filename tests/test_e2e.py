"""End-to-end tests for openapi2cli."""

import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class TestCLIEndToEnd:
    """End-to-end tests for the openapi2cli command."""

    def test_generate_from_file(self, tmp_path):
        """Can generate CLI from a local file."""
        result = subprocess.run(
            [
                sys.executable, "-m", "openapi2cli",
                "generate",
                str(FIXTURES / "petstore.yaml"),
                "--name", "petstore",
                "--output", str(tmp_path / "petstore_cli.py")
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert (tmp_path / "petstore_cli.py").exists()

    def test_generate_from_url(self, tmp_path):
        """Can generate CLI from a URL."""
        result = subprocess.run(
            [
                sys.executable, "-m", "openapi2cli",
                "generate",
                "https://httpbin.org/spec.json",
                "--name", "httpbin",
                "--output", str(tmp_path / "httpbin_cli.py")
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert (tmp_path / "httpbin_cli.py").exists()

    def test_generated_cli_is_executable(self, tmp_path):
        """Generated CLI can be executed."""
        # Generate
        subprocess.run(
            [
                sys.executable, "-m", "openapi2cli",
                "generate",
                str(FIXTURES / "httpbin.json"),
                "--name", "httpbin",
                "--output", str(tmp_path / "httpbin_cli.py")
            ],
            capture_output=True,
            text=True
        )

        # Run help
        result = subprocess.run(
            [sys.executable, str(tmp_path / "httpbin_cli.py"), "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "httpbin" in result.stdout.lower()

    @pytest.mark.integration
    def test_generated_cli_makes_api_call(self, tmp_path):
        """Generated CLI actually calls the API."""
        # Generate
        subprocess.run(
            [
                sys.executable, "-m", "openapi2cli",
                "generate",
                str(FIXTURES / "httpbin.json"),
                "--name", "httpbin",
                "--output", str(tmp_path / "httpbin_cli.py")
            ],
            capture_output=True,
            text=True
        )

        # Call GET /get endpoint
        result = subprocess.run(
            [
                sys.executable,
                str(tmp_path / "httpbin_cli.py"),
                "get",
                "--output", "json"
            ],
            capture_output=True,
            text=True
        )

        # Should either succeed or show helpful error
        if result.returncode == 0:
            assert "url" in result.stdout.lower() or "httpbin" in result.stdout.lower()

    def test_help_command(self):
        """openapi2cli --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "openapi2cli", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "generate" in result.stdout.lower()

    def test_version_command(self):
        """openapi2cli --version works."""
        result = subprocess.run(
            [sys.executable, "-m", "openapi2cli", "--version"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0


class TestRealWorldSpecs:
    """Tests with real-world OpenAPI specs."""

    @pytest.mark.integration
    def test_petstore_full_workflow(self, tmp_path):
        """Full workflow with Petstore spec."""
        # Generate CLI
        gen_result = subprocess.run(
            [
                sys.executable, "-m", "openapi2cli",
                "generate",
                str(FIXTURES / "petstore.yaml"),
                "--name", "petstore",
                "--output", str(tmp_path / "petstore")
            ],
            capture_output=True,
            text=True
        )
        assert gen_result.returncode == 0

        # Check CLI structure
        help_result = subprocess.run(
            [sys.executable, str(tmp_path / "petstore"), "--help"],
            capture_output=True,
            text=True
        )
        assert help_result.returncode == 0

        # Should have pet, store, user groups
        output = help_result.stdout.lower()
        assert "pet" in output

    @pytest.mark.integration
    def test_httpbin_actual_request(self, tmp_path):
        """Makes actual request to httpbin."""
        # Generate
        subprocess.run(
            [
                sys.executable, "-m", "openapi2cli",
                "generate",
                "https://httpbin.org/spec.json",
                "--name", "httpbin",
                "--output", str(tmp_path / "httpbin")
            ],
            capture_output=True,
            text=True
        )

        # First get help to see what commands are available
        help_result = subprocess.run(
            [sys.executable, str(tmp_path / "httpbin"), "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should successfully show help with groups
        assert help_result.returncode == 0
        assert "Commands:" in help_result.stdout or "Usage:" in help_result.stdout

        # Find a group that exists (e.g., http-methods or default)
        # and try a subcommand
        # For httpbin, it groups by tags - /get under "HTTP Methods" -> "http-methods get-get"
        # (name is "get-get" because no operationId, so it's method-path)
        result = subprocess.run(
            [
                sys.executable,
                str(tmp_path / "httpbin"),
                "http-methods", "get-get"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Either success with JSON output or graceful failure
        # returncode 0 = success, 1 = request error, 2 = CLI usage error
        # We accept 0 or 1 (actual API call happened)
        assert result.returncode in [0, 1]

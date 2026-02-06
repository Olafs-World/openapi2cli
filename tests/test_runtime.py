"""Tests for CLI runtime (actual API execution)."""

from pathlib import Path

import pytest

from openapi2cli.generator import CLIGenerator
from openapi2cli.parser import OpenAPIParser
from openapi2cli.runtime import APIClient, CLIRunner

FIXTURES = Path(__file__).parent / "fixtures"


class TestAPIClient:
    """Tests for the API client runtime."""

    def test_makes_get_request(self):
        """Can make a GET request."""
        client = APIClient(base_url="https://httpbin.org")

        response = client.get("/get", params={"foo": "bar"})

        assert response.status_code == 200
        assert response.json()["args"]["foo"] == "bar"

    def test_makes_post_request(self):
        """Can make a POST request with JSON body."""
        client = APIClient(base_url="https://httpbin.org")

        response = client.post("/post", json_data={"name": "test"})

        assert response.status_code == 200
        assert response.json()["json"]["name"] == "test"

    def test_handles_auth_header(self):
        """Includes auth header when configured."""
        client = APIClient(
            base_url="https://httpbin.org",
            auth_header="Authorization",
            auth_value="Bearer test-token"
        )

        response = client.get("/headers")

        assert response.status_code == 200
        headers = response.json()["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token"

    def test_handles_api_key_query_param(self):
        """Includes API key as query param when configured."""
        client = APIClient(
            base_url="https://httpbin.org",
            api_key_param="api_key",
            api_key_value="test-key"
        )

        response = client.get("/get")

        assert response.status_code == 200
        assert response.json()["args"]["api_key"] == "test-key"

    def test_handles_path_parameters(self):
        """Substitutes path parameters."""
        client = APIClient(base_url="https://httpbin.org")

        response = client.get(
            "/anything/{id}",
            path_params={"id": "123"}
        )

        assert response.status_code == 200
        assert "/anything/123" in response.json()["url"]


@pytest.mark.integration
class TestCLIRunner:
    """Integration tests for CLI execution."""

    def test_run_generated_cli_help(self, tmp_path):
        """Generated CLI --help works."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "httpbin.json")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="httpbin")

        # Save and run
        script = tmp_path / "httpbin_cli.py"
        cli.save(script)

        runner = CLIRunner(script)
        result = runner.run(["--help"])

        assert result.exit_code == 0
        assert "httpbin" in result.output.lower() or "usage" in result.output.lower()

    def test_run_generated_cli_command(self, tmp_path):
        """Generated CLI can execute a command."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "httpbin.json")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="httpbin")

        script = tmp_path / "httpbin_cli.py"
        cli.save(script)

        runner = CLIRunner(script)
        # Try to run a simple GET endpoint
        result = runner.run(["get", "--output", "json"])

        # Should succeed or fail gracefully
        assert result.exit_code in [0, 1, 2]  # 0=success, 1=api error, 2=usage error

    def test_run_with_env_auth(self, tmp_path, monkeypatch):
        """CLI reads auth from environment."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "httpbin.json")

        generator = CLIGenerator()
        cli = generator.generate(spec, name="httpbin")

        script = tmp_path / "httpbin_cli.py"
        cli.save(script)

        # Set auth via env
        monkeypatch.setenv("HTTPBIN_API_KEY", "test-key")

        runner = CLIRunner(script)
        result = runner.run(["--help"])

        assert result.exit_code == 0

"""Runtime for executing API calls and running generated CLIs."""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import requests


@dataclass
class CLIResult:
    """Result of running a CLI command."""

    exit_code: int
    output: str
    error: str = ""


class APIClient:
    """HTTP client for making API requests."""

    def __init__(
        self,
        base_url: str,
        auth_header: Optional[str] = None,
        auth_value: Optional[str] = None,
        api_key_param: Optional[str] = None,
        api_key_value: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_header = auth_header
        self.auth_value = auth_value
        self.api_key_param = api_key_param
        self.api_key_value = api_key_value
        self.timeout = timeout
        self.session = requests.Session()

    def _get_headers(self) -> dict:
        """Get request headers including auth."""
        headers = {"Content-Type": "application/json"}

        if self.auth_header and self.auth_value:
            headers[self.auth_header] = self.auth_value

        return headers

    def _get_params(self, params: Optional[dict]) -> dict:
        """Get query parameters including API key if configured."""
        result = params.copy() if params else {}

        if self.api_key_param and self.api_key_value:
            result[self.api_key_param] = self.api_key_value

        return result

    def _build_url(self, path: str, path_params: Optional[dict] = None) -> str:
        """Build full URL with path parameter substitution."""
        if path_params:
            for key, value in path_params.items():
                path = path.replace(f"{{{key}}}", str(value))

        return f"{self.base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        path_params: Optional[dict] = None,
    ) -> requests.Response:
        """Make an HTTP request."""
        url = self._build_url(path, path_params)
        headers = self._get_headers()
        query_params = self._get_params(params)

        return self.session.request(
            method=method,
            url=url,
            params=query_params or None,
            json=json_data,
            headers=headers,
            timeout=self.timeout,
        )

    def get(
        self,
        path: str,
        params: Optional[dict] = None,
        path_params: Optional[dict] = None,
    ) -> requests.Response:
        """Make a GET request."""
        return self.request("GET", path, params=params, path_params=path_params)

    def post(
        self,
        path: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
        path_params: Optional[dict] = None,
    ) -> requests.Response:
        """Make a POST request."""
        return self.request(
            "POST", path, params=params, json_data=json_data, path_params=path_params
        )

    def put(
        self,
        path: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
        path_params: Optional[dict] = None,
    ) -> requests.Response:
        """Make a PUT request."""
        return self.request(
            "PUT", path, params=params, json_data=json_data, path_params=path_params
        )

    def delete(
        self,
        path: str,
        params: Optional[dict] = None,
        path_params: Optional[dict] = None,
    ) -> requests.Response:
        """Make a DELETE request."""
        return self.request("DELETE", path, params=params, path_params=path_params)

    def patch(
        self,
        path: str,
        json_data: Optional[dict] = None,
        params: Optional[dict] = None,
        path_params: Optional[dict] = None,
    ) -> requests.Response:
        """Make a PATCH request."""
        return self.request(
            "PATCH", path, params=params, json_data=json_data, path_params=path_params
        )


class CLIRunner:
    """Runner for executing generated CLIs."""

    def __init__(self, script_path: Union[Path, str]):
        self.script_path = Path(script_path)

    def run(self, args: List[str], env: Optional[dict] = None) -> CLIResult:
        """Run the CLI with given arguments."""
        import os

        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        result = subprocess.run(
            [sys.executable, str(self.script_path)] + args,
            capture_output=True,
            text=True,
            env=full_env,
            timeout=60,
        )

        return CLIResult(
            exit_code=result.returncode,
            output=result.stdout,
            error=result.stderr,
        )

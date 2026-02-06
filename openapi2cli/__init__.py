"""api2cli - Generate CLI tools from OpenAPI specs."""

__version__ = "0.1.0"

from .generator import CLIGenerator, GeneratedCLI
from .parser import Endpoint, OpenAPIParser, Parameter, ParsedSpec
from .runtime import APIClient

__all__ = [
    "OpenAPIParser",
    "ParsedSpec",
    "Endpoint",
    "Parameter",
    "CLIGenerator",
    "GeneratedCLI",
    "APIClient",
]

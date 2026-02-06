"""OpenAPI spec parser."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
import yaml


@dataclass
class Parameter:
    """An API endpoint parameter."""

    name: str
    location: str  # path, query, header, cookie
    required: bool = False
    description: str = ""
    schema_type: str = "string"
    default: Any = None
    enum: List[str] = field(default_factory=list)

    @property
    def cli_name(self) -> str:
        """Convert to CLI option name."""
        # petId -> pet-id, api_key -> api-key
        name = re.sub(r'([a-z])([A-Z])', r'\1-\2', self.name)
        name = name.replace('_', '-').lower()
        return f"--{name}"


@dataclass
class RequestBody:
    """Request body schema."""

    content_type: str = "application/json"
    required: bool = False
    properties: Dict[str, Any] = field(default_factory=dict)
    required_props: List[str] = field(default_factory=list)


@dataclass
class AuthScheme:
    """Authentication scheme."""

    name: str
    type: str  # apiKey, http, oauth2, openIdConnect
    location: str = ""  # header, query, cookie (for apiKey)
    scheme: str = ""  # bearer, basic (for http)
    param_name: str = ""  # name of the header/query param


@dataclass
class Endpoint:
    """An API endpoint."""

    path: str
    method: str
    operation_id: str = ""
    summary: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[Parameter] = field(default_factory=list)
    request_body: Optional[RequestBody] = None
    security: List[str] = field(default_factory=list)

    @property
    def cli_name(self) -> str:
        """Generate CLI command name."""
        if self.operation_id:
            # getPetById -> get-pet-by-id -> get (simplified)
            name = re.sub(r'([a-z])([A-Z])', r'\1-\2', self.operation_id)
            name = name.lower()

            # Simplify common patterns
            # getPetById -> get, listPets -> list, addPet -> add
            parts = name.split('-')
            if len(parts) >= 2:
                # Keep first part and maybe second if it's meaningful
                verb = parts[0]
                if verb in ('get', 'list', 'find', 'add', 'create', 'update', 'delete', 'remove'):
                    if len(parts) > 2 and parts[-1] not in ('by', 'all'):
                        # get-pet-by-id -> get-by-id
                        return '-'.join([verb] + parts[2:])
                    return verb
            return name

        # Fallback: method + simplified path
        path_parts = [p for p in self.path.split('/') if p and not p.startswith('{')]
        if path_parts:
            return f"{self.method.lower()}-{'-'.join(path_parts[-2:])}"
        return self.method.lower()


@dataclass
class ParsedSpec:
    """A parsed OpenAPI specification."""

    title: str
    version: str
    description: str = ""
    base_url: str = ""
    endpoints: List[Endpoint] = field(default_factory=list)
    auth_schemes: List[AuthScheme] = field(default_factory=list)

    def group_by_tag(self) -> Dict[str, List[Endpoint]]:
        """Group endpoints by their tags."""
        groups: Dict[str, List[Endpoint]] = {}

        for endpoint in self.endpoints:
            tags = endpoint.tags or ["default"]
            for tag in tags:
                if tag not in groups:
                    groups[tag] = []
                groups[tag].append(endpoint)

        return groups


class OpenAPIParser:
    """Parser for OpenAPI 3.x specifications."""

    def parse(self, source: Union[str, Path]) -> ParsedSpec:
        """Parse an OpenAPI spec from a file path or URL."""
        raw = self._load_spec(source)
        return self._parse_spec(raw)

    def _load_spec(self, source: Union[str, Path]) -> dict:
        """Load spec from file or URL."""
        if isinstance(source, Path):
            source = str(source)

        # Check if URL
        if source.startswith(('http://', 'https://')):
            response = requests.get(source, timeout=30)
            response.raise_for_status()
            content = response.text
            # Detect format
            if source.endswith('.yaml') or source.endswith('.yml'):
                return yaml.safe_load(content)
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return yaml.safe_load(content)

        # Local file
        path = Path(source)
        content = path.read_text()

        if path.suffix in ('.yaml', '.yml'):
            return yaml.safe_load(content)
        return json.loads(content)

    def _parse_spec(self, raw: dict) -> ParsedSpec:
        """Parse raw spec dict into ParsedSpec."""
        info = raw.get('info', {})

        # Get base URL from servers
        servers = raw.get('servers', [])
        base_url = servers[0]['url'] if servers else ""

        # Parse endpoints
        endpoints = self._parse_paths(raw.get('paths', {}), raw)

        # Parse auth schemes
        auth_schemes = self._parse_security_schemes(
            raw.get('components', {}).get('securitySchemes', {})
        )

        return ParsedSpec(
            title=info.get('title', 'API'),
            version=info.get('version', '1.0.0'),
            description=info.get('description', ''),
            base_url=base_url,
            endpoints=endpoints,
            auth_schemes=auth_schemes,
        )

    def _parse_paths(self, paths: dict, spec: dict) -> List[Endpoint]:
        """Parse paths into endpoints."""
        endpoints = []

        for path, methods in paths.items():
            # Handle path-level parameters
            path_params = self._parse_parameters(
                methods.get('parameters', []), spec
            )

            for method, details in methods.items():
                if method in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options'):
                    endpoint = self._parse_endpoint(
                        path, method.upper(), details, spec, path_params
                    )
                    endpoints.append(endpoint)

        return endpoints

    def _parse_endpoint(
        self,
        path: str,
        method: str,
        details: dict,
        spec: dict,
        path_params: List[Parameter]
    ) -> Endpoint:
        """Parse a single endpoint."""
        # Parse parameters (combine path-level and operation-level)
        params = path_params.copy()
        params.extend(
            self._parse_parameters(details.get('parameters', []), spec)
        )

        # Parse request body
        request_body = None
        if 'requestBody' in details:
            request_body = self._parse_request_body(details['requestBody'], spec)

        # Get security requirements
        security = []
        for sec in details.get('security', []):
            security.extend(sec.keys())

        return Endpoint(
            path=path,
            method=method,
            operation_id=details.get('operationId', ''),
            summary=details.get('summary', ''),
            description=details.get('description', ''),
            tags=details.get('tags', []),
            parameters=params,
            request_body=request_body,
            security=security,
        )

    def _parse_parameters(self, params: list, spec: dict) -> List[Parameter]:
        """Parse parameters."""
        result = []

        for param in params:
            # Handle $ref
            if '$ref' in param:
                param = self._resolve_ref(param['$ref'], spec)

            schema = param.get('schema', {})

            result.append(Parameter(
                name=param.get('name', ''),
                location=param.get('in', 'query'),
                required=param.get('required', False),
                description=param.get('description', ''),
                schema_type=schema.get('type', 'string'),
                default=schema.get('default'),
                enum=schema.get('enum', []),
            ))

        return result

    def _parse_request_body(self, body: dict, spec: dict) -> RequestBody:
        """Parse request body."""
        # Handle $ref
        if '$ref' in body:
            body = self._resolve_ref(body['$ref'], spec)

        content = body.get('content', {})

        # Prefer JSON
        content_type = 'application/json'
        if content_type not in content:
            content_type = next(iter(content.keys()), 'application/json')

        schema = content.get(content_type, {}).get('schema', {})

        # Handle $ref in schema
        if '$ref' in schema:
            schema = self._resolve_ref(schema['$ref'], spec)

        properties = schema.get('properties', {})
        required_props = schema.get('required', [])

        return RequestBody(
            content_type=content_type,
            required=body.get('required', False),
            properties=properties,
            required_props=required_props,
        )

    def _parse_security_schemes(self, schemes: dict) -> List[AuthScheme]:
        """Parse security schemes."""
        result = []

        for name, details in schemes.items():
            scheme_type = details.get('type', '')

            auth = AuthScheme(
                name=name,
                type=scheme_type,
            )

            if scheme_type == 'apiKey':
                auth.location = details.get('in', 'header')
                auth.param_name = details.get('name', '')
            elif scheme_type == 'http':
                auth.scheme = details.get('scheme', 'bearer')

            result.append(auth)

        return result

    def _resolve_ref(self, ref: str, spec: dict) -> dict:
        """Resolve a $ref pointer."""
        if not ref.startswith('#/'):
            return {}

        parts = ref[2:].split('/')
        current = spec

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return {}

        return current if isinstance(current, dict) else {}

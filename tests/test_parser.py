"""Tests for OpenAPI spec parsing."""

from pathlib import Path

from openapi2cli.parser import OpenAPIParser, ParsedSpec

FIXTURES = Path(__file__).parent / "fixtures"


class TestOpenAPIParser:
    """Tests for the OpenAPI parser."""

    def test_parse_petstore_yaml(self):
        """Can parse a YAML OpenAPI spec."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        assert isinstance(spec, ParsedSpec)
        assert spec.title == "OpenAPI Petstore"
        assert spec.version == "1.0.0"
        assert spec.base_url == "http://petstore.swagger.io/v2"

    def test_parse_httpbin_json(self):
        """Can parse a JSON OpenAPI spec."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "httpbin.json")

        assert isinstance(spec, ParsedSpec)
        assert spec.title == "httpbin.org"

    def test_parse_from_url(self):
        """Can parse a spec from a URL."""
        parser = OpenAPIParser()
        spec = parser.parse("https://httpbin.org/spec.json")

        assert spec.title == "httpbin.org"

    def test_extracts_endpoints(self):
        """Extracts endpoints from paths."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        assert len(spec.endpoints) > 0

        # Find the listPets endpoint
        list_pets = next(
            (e for e in spec.endpoints if e.operation_id == "getPetById"),
            None
        )
        assert list_pets is not None
        assert list_pets.method == "GET"
        assert list_pets.path == "/pet/{petId}"

    def test_extracts_parameters(self):
        """Extracts parameters from endpoints."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        # Find endpoint with path parameter
        get_pet = next(
            (e for e in spec.endpoints if e.operation_id == "getPetById"),
            None
        )
        assert get_pet is not None

        # Should have petId as path parameter
        pet_id_param = next(
            (p for p in get_pet.parameters if p.name == "petId"),
            None
        )
        assert pet_id_param is not None
        assert pet_id_param.location == "path"
        assert pet_id_param.required is True

    def test_extracts_request_body(self):
        """Extracts request body schema from endpoints."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        # Find POST /pet endpoint
        add_pet = next(
            (e for e in spec.endpoints if e.operation_id == "addPet"),
            None
        )
        assert add_pet is not None
        assert add_pet.request_body is not None
        assert "name" in add_pet.request_body.properties

    def test_extracts_auth_schemes(self):
        """Extracts authentication schemes."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        assert len(spec.auth_schemes) > 0
        # Petstore uses api_key and oauth2
        scheme_types = [s.type for s in spec.auth_schemes]
        assert "apiKey" in scheme_types or "oauth2" in scheme_types

    def test_groups_endpoints_by_tag(self):
        """Groups endpoints by their tags."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        grouped = spec.group_by_tag()

        assert "pet" in grouped
        assert "store" in grouped
        assert "user" in grouped
        assert len(grouped["pet"]) > 0


class TestParsedSpec:
    """Tests for the ParsedSpec data class."""

    def test_to_cli_name(self):
        """Converts operation IDs to CLI-friendly names."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "petstore.yaml")

        endpoint = next(
            (e for e in spec.endpoints if e.operation_id == "getPetById"),
            None
        )
        assert endpoint is not None
        # getPetById -> get-pet-by-id or get
        assert endpoint.cli_name in ["get-pet-by-id", "get", "get-by-id"]

    def test_infers_cli_name_from_method_and_path(self):
        """Infers CLI name when operationId is missing."""
        parser = OpenAPIParser()
        spec = parser.parse(FIXTURES / "httpbin.json")

        # HTTPBin endpoints might not have operationIds
        # Should still generate usable names
        for endpoint in spec.endpoints[:5]:
            assert endpoint.cli_name is not None
            assert len(endpoint.cli_name) > 0

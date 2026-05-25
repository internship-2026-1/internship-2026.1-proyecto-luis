GATEWAY_REQUIRED_HEADERS = [
    {
        "name": "x-api-key",
        "in": "header",
        "required": True,
        "schema": {"type": "string"},
        "description": "API key requerida por el gateway.",
    },
    {
        "name": "x-origin",
        "in": "header",
        "required": True,
        "schema": {"type": "string"},
        "description": "Origen requerido por el gateway.",
    },
]


def inject_gateway_servers(result, generator, request, public):
    """Inject gateway server URL and required gateway headers into the OpenAPI schema."""
    servers = result.get("servers", [])
    gateway_url = {"url": "/core/api/v1"}
    if gateway_url not in servers:
        servers.append(gateway_url)
    result["servers"] = servers

    for path_item in result.get("paths", {}).values():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue

            parameters = operation.setdefault("parameters", [])
            existing_headers = {
                (parameter.get("name", "").lower(), parameter.get("in"))
                for parameter in parameters
            }

            for header in GATEWAY_REQUIRED_HEADERS:
                header_key = (header["name"].lower(), header["in"])
                if header_key not in existing_headers:
                    parameters.append(header.copy())

    return result
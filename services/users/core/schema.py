def inject_gateway_servers(result, generator, request, public):
    """Inject gateway server URL into the OpenAPI schema if missing."""
    servers = result.get("servers", [])
    gateway_url = {"url": "/user/api/v1"}
    if gateway_url not in servers:
        servers.append(gateway_url)
    result["servers"] = servers
    return result
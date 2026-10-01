from app.core.process_role import mark_connector_resource
mark_connector_resource()
import json, os, httpx
from app.mcp.connector.asgi import create_app
from app.mcp.connector.settings import ConnectorSettings
from app.mcp.connector_shared.verifier import ConnectorTokenVerifier
JWKS = json.load(open(os.environ["S1786_LOCAL_JWKS_FILE"]))   # public keys only
CANON = "https://auth.ai.market/.well-known/jwks.json"
def route(req):
    return httpx.Response(200, json=JWKS) if str(req.url) == CANON else httpx.Response(404)
app = create_app(ConnectorSettings.from_env(),
                 verifier=ConnectorTokenVerifier(client=httpx.AsyncClient(transport=httpx.MockTransport(route))))

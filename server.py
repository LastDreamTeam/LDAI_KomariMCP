# SPDX-License-Identifier: AGPL-3.0-only
"""Stdio MCP adapter for an operator-selected Komari deployment."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

mcp = FastMCP("komari")
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None

def access_key():
    filename = os.getenv("KOMARI_API_KEY_FILE")
    if filename:
        try:
            return Path(filename).expanduser().read_text(encoding="utf-8-sig").strip()
        except OSError:
            raise ValueError("Cannot read KOMARI_API_KEY_FILE.") from None
    return os.getenv("KOMARI_API_KEY", "").strip()

def public(value):
    if isinstance(value, list):
        return [public(v) for v in value]
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items()
                if not any(s in k.lower().replace("_","") for s in
                           ("password","token","secret","apikey","privatekey","authorization","cookie"))}
    return value

def api(path, body=None):
    base = os.getenv("KOMARI_BASE_URL", "").rstrip("/")
    url = urlsplit(base)
    if not url.hostname or url.username or url.password or url.query or url.fragment or not (
        url.scheme == "https" or url.scheme == "http" and url.hostname in ("localhost","127.0.0.1","::1")
    ):
        raise ValueError("Set KOMARI_BASE_URL to an HTTPS dashboard or an HTTP loopback address.")
    key = access_key()
    headers = {"Accept":"application/json","Content-Type":"application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    if path.startswith("/api/admin/") and not key:
        raise ValueError("Configure your Komari administrator API key.")
    req = Request(base + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
    try:
        with build_opener(NoRedirect()).open(req, timeout=25) as response:
            data = response.read(8 * 1024 * 1024 + 1)
    except HTTPError as exc:
        raise ValueError(f"Komari returned HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("Komari connection failed. Check the dashboard URL and TLS trust.") from None
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("Result too large. Request a shorter time range.")
    try:
        value = json.loads(data)
    except (ValueError, UnicodeError):
        raise ValueError("Komari returned an invalid JSON document.") from None
    if isinstance(value, dict):
        if value.get("error") or value.get("status") == "error":
            raise ValueError("Komari rejected the operation. Check version and authorization.")
        if "result" in value and "jsonrpc" in value:
            value = value["result"]
        elif "data" in value and "status" in value:
            value = value["data"]
    return public(value)

@mcp.tool()
def komari_status():
    """Read the dashboard version."""
    return api("/api/version")

@mcp.tool()
def komari_list_servers():
    """List visible nodes using the public or authenticated endpoint."""
    return api("/api/admin/client/list" if access_key() else "/api/nodes")

@mcp.tool()
def komari_get_server(uuid: UUID):
    """Read a node's administrative metadata."""
    return api("/api/admin/client/" + str(uuid))

@mcp.tool()
def komari_latest_status(uuid: UUID | None = None):
    """Fetch CPU, memory and network readings for one or all visible nodes."""
    return api("/api/rpc2", {"jsonrpc":"2.0","id":1,"method":"common:getNodesLatestStatus",
                             "params":{"uuid":str(uuid)} if uuid else {}})

@mcp.tool()
def komari_monitor_records(uuid: UUID, kind: Literal["load","ping"], hours: Annotated[int, Field(ge=1,le=168)] = 1,
                           load_type: str | None = None, task_id: int | None = None):
    """Fetch a bounded history page, retaining the last 500 records."""
    query = {"uuid":str(uuid),"hours":hours}
    if load_type:
        query["load_type"] = load_type
    if task_id is not None:
        query["task_id"] = task_id
    result = api("/api/records/" + kind + "?" + urlencode(query))
    if isinstance(result, dict) and isinstance(result.get("records"), list):
        result["truncated"] = len(result["records"]) > 500
        result["records"] = result["records"][-500:]
    return result

@mcp.tool()
def komari_list_ping_tasks():
    """List configured network checks."""
    return api("/api/admin/ping/")

@mcp.tool()
def komari_list_plugins():
    """List dashboard plugins."""
    return api("/api/admin/plugin/list")

@mcp.tool()
def komari_list_themes():
    """List dashboard themes."""
    return api("/api/admin/theme/list")

class Changes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=1, max_length=100)
    group: str | None = None
    tags: str | None = None
    remark: str | None = None
    public_remark: str | None = None
    expired_at: datetime | None = None
    price: float | None = Field(None, ge=0, allow_inf_nan=False)
    currency: str | None = None
    billing_cycle: int | None = Field(None, ge=1)
    traffic_limit: int | None = Field(None, ge=0)
    traffic_limit_type: Literal["sum","up","down","max"] | None = None
    auto_renewal: bool | None = None
    hidden: bool | None = None
    weight: int | None = None

@mcp.tool()
def komari_update_server(uuid: UUID, fields: Changes):
    """Update only supplied metadata fields, then read back changed values. No automatic retry."""
    change = fields.model_dump(mode="json", exclude_none=True)
    if not change or fields.expired_at and fields.expired_at.tzinfo is None:
        raise ValueError("Supply at least one field and include a timezone for expiry.")
    before = komari_get_server(uuid)
    if not isinstance(before, dict) or before.get("uuid") != str(uuid):
        raise ValueError("Unable to confirm the node before updating.")
    api("/api/admin/client/" + str(uuid) + "/edit", change)
    after = komari_get_server(uuid)
    previous = {k: before.get(k) for k in change}
    observed = {k: after.get(k) for k in change}
    def matches(k):
        if k == "expired_at" and observed[k]:
            return datetime.fromisoformat(observed[k].replace("Z","+00:00")) == fields.expired_at
        return observed[k] == change[k]
    return {"verified":all(matches(k) for k in change), "previous":previous, "observed":observed}

if __name__ == "__main__":
    mcp.run(transport="stdio")

"""Run the local no-Qdrant rehearsal and assert its meaningful outcomes."""
import argparse
import json
from pathlib import Path
import httpx

def run(fixtures, token_file, url):
    ids=json.loads(Path(fixtures).read_text())
    headers={"Host":"connect.ai.market", "Authorization":"Bearer "+Path(token_file).read_text().strip(), "Accept":"application/json, text/event-stream", "MCP-Protocol-Version":"2025-11-25"}
    responses={}
    with httpx.Client(headers=headers, timeout=60, trust_env=False) as c:
        def call(label, method, params, number):
            r=c.post(url, json={"jsonrpc":"2.0", "id":number, "method":method, "params":params})
            print(json.dumps({"call":label,"status":r.status_code,"request_id":r.headers.get("x-request-id"),"body":r.text}),flush=True)
            r.raise_for_status()
            if r.headers.get("mcp-session-id"):
                c.headers["MCP-Session-Id"]=r.headers["mcp-session-id"]
            if r.text.startswith("event:"):
                body=json.loads(next(line[6:] for line in r.text.splitlines() if line.startswith("data: ")))
            else:
                body=r.json()
            assert "error" not in body, body
            responses[label]=(r,body)
            return body.get("result",{})
        call("initialize","initialize",{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"S1786 SYNTHETIC TEST","version":"1"}},1)
        tools=call("tools/list","tools/list",{},2)
        assert {t["name"] for t in tools["tools"]} == {"search_listings","get_listing","get_my_account","get_activity","list_data_requests"}
        for n,name in enumerate(("get_my_account","get_activity","list_data_requests"),3):
            result=call(name,"tools/call",{"name":name,"arguments":{}},n)
            assert not result.get("isError"), result
        for n,label in enumerate(("L1","L2","L3"),6):
            result=call(label,"tools/call",{"name":"get_listing","arguments":{"listing_id":ids[label]}},7 if label=="L3" else n)
            if label == "L1":
                assert not result.get("isError"), result
                data=result["structuredContent"]
                assert all(k in data for k in ("title","summary","category","price","update_frequency","schema","preview"))
                assert len(data["schema"]["columns"])>=2 and data["schema"]["row_count"]>=5
                assert data["preview"]["kind"]=="schema_stats"
            else:
                assert result.get("isError") and result["structuredContent"]["error"]["code"]=="NOT_FOUND", result
        # Use the same JSON-RPC correlation ID for L2/L3 so the complete
        # wire envelopes can be compared byte-for-byte except request IDs.
        envelopes=[]
        for label in ("L2","L3"):
            r,body=responses[label]
            envelopes.append(r.content.replace(r.headers["x-request-id"].encode(), b"<request_id>"))
        assert envelopes[0]==envelopes[1], envelopes
        result=call("search_listings","tools/call",{"name":"search_listings","arguments":{"query":ids["literal_token"]}},9)
        assert not result.get("isError"), result
        data=result["structuredContent"]
        assert data["search_mode"]=="sql_fallback", data
        assert ids["L4"] in {i["id"] for i in data["items"]}, data
        assert "TEMPORARILY_UNAVAILABLE" not in json.dumps(result)
    print("PASS: exact five tools; private reads; ListingOutput; equal NOT_FOUND tool envelopes; SQL fallback includes L4",flush=True)

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixtures",required=True)
    p.add_argument("--token-file",required=True)
    p.add_argument("--url",default="http://127.0.0.1:8080/mcp")
    a=p.parse_args()
    run(a.fixtures,a.token_file,a.url)

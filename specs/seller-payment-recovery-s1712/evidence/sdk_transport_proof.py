"""Local HTTP transport proof only. No Stripe endpoint or financial effects."""
import asyncio, hashlib, json, time
import stripe, httpx
from pathlib import Path

async def exercise(hang=False):
    calls=[]
    closed=asyncio.Event()
    async def handle(reader, writer):
        try:
            raw=await reader.readuntil(b"\r\n\r\n")
            headers=dict(line.split(":",1) for line in raw.decode().split("\r\n")[1:] if ":" in line)
            headers={k.lower():v.strip() for k,v in headers.items()}
            body=await reader.readexactly(int(headers.get("content-length",0)))
            calls.append({"body_sha256":hashlib.sha256(body).hexdigest(),"idempotency_key":headers.get("idempotency-key")})
            if hang:
                await reader.read()
                closed.set()
                return
            retry=len(calls)<3
            payload=json.dumps({"error":{"message":"local retry","type":"api_error"}} if retry else {"id":"pi_local_test","object":"payment_intent","status":"processing"}).encode()
            status="500 Internal Server Error" if retry else "200 OK"
            writer.write((f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\nStripe-Should-Retry: true\r\nContent-Length: {len(payload)}\r\nConnection: close\r\n\r\n").encode()+payload)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
    server=await asyncio.start_server(handle,"127.0.0.1",0)
    port=server.sockets[0].getsockname()[1]
    transport=stripe.HTTPXClient(timeout=httpx.Timeout(5.0,connect=2.0,pool=2.0))
    client=stripe.StripeClient("local-test-only",http_client=transport,max_network_retries=2,base_addresses={"api":f"http://127.0.0.1:{port}"})
    start=time.monotonic(); outcome=None
    try:
        async with asyncio.timeout(0.25 if hang else 20):
            result=await client.v1.payment_intents.create_async({"amount":100,"currency":"usd"},{"idempotency_key":"local-original-request"})
            outcome=result.id
    except TimeoutError:
        assert hang
    finally:
        await transport.close_async()
        server.close();await server.wait_closed()
    elapsed=time.monotonic()-start
    if hang:
        await asyncio.wait_for(closed.wait(),2)
        assert len(calls)==1
    else:
        assert len(calls)==3 and calls[0]==calls[1]==calls[2] and outcome=="pi_local_test"
    return {"calls":calls,"elapsed_s":elapsed,"outcome":outcome,"socket_closed":closed.is_set()}

async def main():
    result={"stripe_version":stripe.VERSION,"httpx_version":httpx.__version__,"configured_retries":2,"retry":await exercise(),"cancel":await exercise(True),"scope":"localhost only; accelerated0.25s cancellation, not full20s workflow proof"}
    path=Path(__file__).with_name("SDK-ASYNC-TRANSPORT-REPRODUCED.json")
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))

if __name__=="__main__":
    asyncio.run(main())

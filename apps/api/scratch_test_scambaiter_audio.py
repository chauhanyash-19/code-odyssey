import asyncio
import httpx
import websockets

async def run_test():
    print("1. Starting Call Init...")
    async with httpx.AsyncClient() as client:
        res = await client.post("http://127.0.0.1:10000/call/init", json={"ingestion_mode": "browser_mic"})
        data = res.json()
        call_id = data["call_id"]
        token = data["token"]
        ws_url = f"ws://127.0.0.1:10000/ws/call/{call_id}?token={token}"
        
        print(f"2. Connecting to WebSocket {ws_url}")
        async with websockets.connect(ws_url) as ws:
            msg = await ws.recv()
            print("Received WS Text:", msg)
            msg = await ws.recv()
            print("Received WS Text:", msg)
            
            print("3. Activating scambaiter via REST...")
            res = await client.post(
                f"http://127.0.0.1:10000/call/{call_id}/scambait", 
                headers={"Authorization": f"Bearer {token}"}
            )
            print("Scambaiter active:", res.json())
            
            print("4. Injecting fake scammer speech 'mera bank OTP batao' directly to backend...")
            res = await client.post(
                f"http://127.0.0.1:10000/call/{call_id}/test_inject", 
                params={"text": "mera bank OTP batao"}
            )
            print("Injected text:", res.json())
            
            print("Waiting for Scambaiter response over WebSocket...")
            while True:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=20.0)
                    if isinstance(response, str):
                        print("Received WS Text:", response)
                    else:
                        print("\n=======================================================")
                        print(f"SUCCESS! RECEIVED RAW BINARY AUDIO BYTES FROM SCAMBAITER!")
                        print(f"Payload Size: {len(response)} bytes")
                        print("=======================================================\n")
                        
                        # Save the audio as raw evidence
                        with open("scambait_evidence.raw", "wb") as f:
                            f.write(response)
                        print("Saved to scambait_evidence.raw")
                        break
                except asyncio.TimeoutError:
                    print("Timeout waiting for scambaiter response!")
                    break

if __name__ == "__main__":
    asyncio.run(run_test())

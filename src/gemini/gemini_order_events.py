import ssl
import websocket
import json
import base64
import hmac
import hashlib
import time
from pathlib import Path
def on_message(ws, message):
    print(message)

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

user_home = str(Path.home())
gemini_api_key_path = user_home + "/.ssh/stars_in_sky.txt"

gemini_api_secret_path = user_home + "/.ssh/stars_aligned"


gemini_api_key = ""
gemini_api_secret = ""
with open(gemini_api_key_path, "r") as f:
    gemini_api_key = f.readline().strip()

with open(gemini_api_secret_path, "r") as f:
    gemini_api_secret = f.readline().strip().encode()

payload = {"request": "/v1/order/events","nonce": time.time()}
encoded_payload = json.dumps(payload).encode()
b64 = base64.b64encode(encoded_payload)
signature = hmac.new(gemini_api_secret, b64, hashlib.sha384).hexdigest()


ws = websocket.WebSocketApp("wss://api.gemini.com/v1/order/events",
                            on_message=on_message,
                            header={
                                'X-GEMINI-PAYLOAD': b64.decode(),
                                'X-GEMINI-APIKEY': gemini_api_key,
                                'X-GEMINI-SIGNATURE': signature
                            })
ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=30)
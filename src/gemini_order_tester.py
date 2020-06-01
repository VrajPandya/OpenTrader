import websocket
import hmac
import requests
import ssl
import json
import base64
import hmac
import hashlib
import datetime, time
from pathlib import Path

def on_order_event_message(ws, message):
    print(message)

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")


base_url = "https://api.gemini.com"
endpoint = "/v1/order/new"
url = base_url + endpoint

user_home = str(Path.home())
gemini_api_key_path = user_home + "/.ssh/stars_in_sky.txt"

gemini_api_secret_path = user_home + "/.ssh/stars_aligned"


gemini_api_key = ""
gemini_api_secret = ""
with open(gemini_api_key_path, "r") as f:
    gemini_api_key = f.readline().strip()

with open(gemini_api_secret_path, "r") as f:
    gemini_api_secret = f.readline().strip().encode()

t = datetime.datetime.now()
payload_nonce = time.time()

payload = {
   "request": "/v1/order/new",
    "nonce": payload_nonce,
    "symbol": "btcusd",
    "amount": "0.01",
    "price": "25533.00",
    "side": "buy",
    "type": "exchange limit",
    "options": [] 
}

encoded_payload = json.dumps(payload).encode()
b64 = base64.b64encode(encoded_payload)
signature = hmac.new(gemini_api_secret, b64, hashlib.sha384).hexdigest()

request_headers = { 'Content-Type': "text/plain",
                    'Content-Length': "0",
                    'X-GEMINI-APIKEY': gemini_api_key,
                    'X-GEMINI-PAYLOAD': b64,
                    'X-GEMINI-SIGNATURE': signature,
                    'Cache-Control': "no-cache" }

response = requests.post(url,
                        data=None,
                        headers=request_headers)

new_order = response.json()
print(new_order)
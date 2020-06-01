import ssl
import websocket
import json
import base64
import hmac
import hashlib
import time
from pathlib import Path
import _thread as thread

def on_message(ws, message):
    # print(ws)
    # print(message)
    message_dict = json.loads(message)
    if message_dict["type"] == "heartbeat":
        return
    if message_dict["type"] == "update":
        events = message_dict["events"]
        for event in events:
            print("type: " + event["type"] + " price " + event["price"])

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    # def run(*args):
    #     
    # thread.start_new_thread(run, ())
    ws.send(candle_sub_msg)

def on_ping(ws, ping_info):
    print(ping_info)
    print("on_ping")

def on_pong(ws, pong_info):
    # print(pong_info)
    print("on_pong")

user_home = str(Path.home())
gemini_api_key_path = user_home + "/.ssh/stars_in_sky.txt"

gemini_api_secret_path = user_home + "/.ssh/stars_aligned"


gemini_api_key = ""
gemini_api_secret = ""
with open(gemini_api_key_path, "r") as f:
    gemini_api_key = f.readline().strip()

with open(gemini_api_secret_path, "r") as f:
    gemini_api_secret = f.readline().strip().encode()

candle_sub_msg ='{ "type": "subscribe","subscriptions": [{"name": "candles_5s","symbols": ["BTCUSD"]}]}'

logon_msg = '{"type": "subscribe","subscriptions":[{"name":"l2","symbols":["BTCUSD"]}]}'

# websocket.enableTrace(True)
payload = {"request": "/v1/order/events","nonce": int(time.time()*1000)}
encoded_payload = json.dumps(payload).encode()
b64 = base64.b64encode(encoded_payload)
signature = hmac.new(gemini_api_secret, b64, hashlib.sha384).hexdigest()


ws = websocket.WebSocketApp("wss://api.gemini.com/v1/marketdata/btcusd?trades=true&top_of_book=true",
                                on_ping = on_ping,
                                on_pong = on_pong,
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close,
                                on_open = on_open)

ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
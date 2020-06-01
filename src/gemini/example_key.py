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
    message_dict = json.loads(message)
    type = message_dict["type"]
    if type == "heartbeat":
        return
    elif type == "trades":
        print(message)
    elif type == "l2_updates":
        changes = message_dict["changes"]
        for change in changes:
            if float(change[2]) > 0:
                print(message)
                return
        if message_dict.keys().__contains__("trades"):
            print(message)
            print(message_dict["trades"])

def print_message(ws, message):
    print(message)

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    # def run(*args):
    #
    # thread.start_new_thread(run, ())
    ws.send(logon_msg)

user_home = str(Path.home())
gemini_api_key_path = user_home + "/.ssh/stars_in_sky.txt"

gemini_api_secret_path = user_home + "/.ssh/stars_aligned"


gemini_api_key = ""
gemini_api_secret = ""
with open(gemini_api_key_path, "r") as f:
    gemini_api_key = f.readline().strip()

with open(gemini_api_secret_path, "r") as f:
    gemini_api_secret = f.readline().strip().encode()

candle_sub_msg ='{ "type": "subscribe","subscriptions": [{"name": "candles_1m","symbols": ["BTCUSD"]}]}'

logon_msg = '{"type": "subscribe","subscriptions":[{"name":"l2","symbols":["BTCUSD"]}]}'

# websocket.enableTrace(True)
payload = {"request": "/v1/order/events","nonce": int(time.time()*1000)}
encoded_payload = json.dumps(payload).encode()
b64 = base64.b64encode(encoded_payload)
signature = hmac.new(gemini_api_secret, b64, hashlib.sha384).hexdigest()


ws = websocket.WebSocketApp("wss://api.gemini.com/v2/marketdata",
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close,
                                on_open = on_open)
ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
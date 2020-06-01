import ssl
import websocket
import json
from datetime import datetime

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# You can generate an API token from the "API Tokens Tab" in the UI
token = "D6wMwL1Kccld0Cu637V62KUFEZTYLNbxf6ItZ1bLNIlxCfdqzRcxxXaRerwnDAK3Xf1D5X3nm6-hx0O4sb5gmw=="
org = "CryptoTrader"
btc_bucket = "btc"
eth_bucket = "eth"
zec_bucket = "zec"
bcs_bucket = "bch"
ltc_bucket = "ltc"

influx_client = InfluxDBClient(url="http://localhost:8086", token=token, org=org)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)


def insert_point(point_to_insert, event_json):
    if event_json["symbol"] == "BTCUSD":
        write_api.write(btc_bucket, org, point_to_insert)

    elif event_json["symbol"] == "ETHUSD":
        write_api.write(eth_bucket, org, point_to_insert)

    elif event_json["symbol"] == "ZECUSD":
        write_api.write(zec_bucket, org, point_to_insert)

    elif event_json["symbol"] == "BCH":
        write_api.write(bcs_bucket, org, point_to_insert)

    elif event_json["symbol"] == "LTCUSD":
        write_api.write(ltc_bucket, org, point_to_insert)

def process_event(event_json, event_time) -> Point:
    price = float(event_json["price"])
    type = event_json["type"]
    result = point = Point("price") \
        .tag("type", type) \
        .field("price", price) \
        .time(event_time, WritePrecision.NS)
    return result

def on_message(ws, message):
    
    # print("=========")
    #print(message)
    message_json = json.loads(message)
    message_events = message_json["events"]

    event_type_str = message_json["type"]
    # print(event_type_str)
    
    time_for_points = datetime.utcnow()
    for event in message_events:    
        point_to_insert = process_event(event, time_for_points)
        insert_point(point_to_insert, event)

influx_client.close()    

# ,ETHUSD,zecusd,bchusd

wss_url = "wss://api.gemini.com/v1/multimarketdata?symbols=BTCUSD,ETHUSD,ZECUSD,BCHUSD,LTCUSD&top_of_book=true&offers=true"
wss_url = "wss://api.gemini.com/v1/marketdata/BTCUSD,ETHUSD,ZECUSD,BCHUSD,LTCUSD?top_of_book=true&offers=true"
ws = websocket.WebSocketApp(
    wss_url,
    on_message=on_message)
ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
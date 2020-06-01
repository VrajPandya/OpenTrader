import datetime
import csv
from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.contract import Contract
import logging

from ibapi.common import *
import traceback

from ibapi.utils import *
from ibapi.order_condition import *
from ibkr_app.utils import contract_helper
from ibapi.order import *
from ibapi.order_state import *

TWS_PAPER_PORT = 7497
TWS_PROD_PORT = 7496

CSV_FILE = "data/btc_historical_data_4_6_2023.csv"

## TODO: Figure out why the simple python invocation of the script doesn't work
## But the debugger invocation works fine.

def createContractDescriptor(symbol, secType, currency, exchange, primaryExchange):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = secType
    contract.currency = currency
    contract.exchange = exchange
    contract.primaryExchange = primaryExchange
    return contract 

class HistoricalDataApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.nextValidOrderId = 0
        self.outputFile = open(CSV_FILE, "w")
        self.csvWriter = csv.writer(self.outputFile)
        self.csvWriter.writerow(["Date", "Open", "High", "Low", "Close", "Volume", "Count", "WAP"])


    @iswrapper
    def nextValidId(self, orderId:int):
        super().nextValidId(orderId)
        logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId
 
    def nextOrderId(self):
        id = self.nextValidOrderId
        self.nextValidOrderId += 1
        return id

    @iswrapper
    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson = ""):
        print("Contract Details: ", reqId, " ", errorCode, " ", errorString, " ")

    def keyboardInterrupt(self):
        self.nKeybInt += 1
        traceback.print_exception(keyboard_int) 
        if self.nKeybInt <= 5:
            self.stop()
        if self.nKeybIntHard > 5:
            self.stop()
            raise SystemExit()

    def stop(self):
        self.disconnect()
 

    def setup(self):
        btc_contract = contract_helper.createContractDescriptor("BTC", "CRYPTO", "USD", "SMART", "PAXOS")
        queryTime = (datetime.datetime.today() - datetime.timedelta(days=2)).strftime("%Y%m%d-%H:%M:%S")
        print("Querying BTC historical data from: "+ queryTime)
        self.reqHistoricalData(self.nextOrderId(), btc_contract, queryTime,
                               "2 D", "5 secs", "MIDPOINT", 1, 1, False, [])
        

    @iswrapper
    def historicalData(self, reqId:int, bar: BarData):
        print("HistoricalData. ReqId:", reqId, "BarData.", bar)
        self.csvWriter.writerow([bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume, bar.barCount, bar.wap])

    @iswrapper
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        print("HistoricalDataEnd. ReqId:", reqId, "from", start, "to", end)
        self.outputFile.close()
        self.stop()

def main():
    app = HistoricalDataApp()
    app.connect("127.0.0.1", TWS_PROD_PORT, 10)
    app.setup()    
    import time
    time.sleep(5)
    app.run()

if __name__ == "__main__":
    main()



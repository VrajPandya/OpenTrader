from trader_ledger.Entry import Entry
from pathlib import Path
import os
import csv

# Current Schema:
# ID, serialized order_desc, latest_execution, commission_report
# 
# addEntry generates a new ID for the entry for the Entry Context to reffer back to.

class LedgerManager:
    def __init__(self, output_format = "CSV", output_path = "") -> None:
        self.output_format = output_format
        self.output_path = output_path + "/TraderLedger/"
        self.file_path = self.output_path + 'ledger.' + self.output_format
        self.last_id = self.checkForExistingLedger()
        if self.last_id == -1:
            self.last_id = 0
            self.writeHeader()
        else:
            self.last_id = self.last_id + 1
        

    def writeHeader(self):
        with open(self.file_path, "a+") as file:
            writer = csv.writer(file)
            writer.writerow(["EntryID", 
                             # Order
                             "OrderID", "ClientID", "Action", "TotalQuantity", 
                             "LimitPrice", "TimeInForce", "FilledQuantity", 
                             # Contract
                             "Symbol", "Exchange", "Currency",
                             # Execution
                             "ExecutionID", "ExecTime", "AvgPrice", 
                             "ExecutionSide",
                             # Commission Report
                             "Commission", "RealizedPNL", "CommissionCurrency", "Yield"])

    def checkForExistingLedger(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as file:
                last_line = list(csv.reader(file))[-1]
                last_col = last_line[0]
                if last_col == "EntryID":
                    return -1
                return int(last_id)
        else:
            return -1

    def addEntry(self, entry: Entry):
        cur_id = self.last_id
        with open(self.file_path, 'a') as file:
            writer = csv.writer(file)
            list_of_elements = [cur_id, 
                                # Order
                                entry.order_desc.orderID, entry.order_desc.orderInfo.clientId, 
                                entry.order_desc.orderInfo.action, entry.order_desc.orderInfo.totalQuantity,
                                entry.order_desc.orderInfo.lmtPrice, entry.order_desc.orderInfo.tif,
                                entry.order_desc.orderInfo.filledQuantity,
                                # Contract
                                entry.order_desc.contractInfo.symbol, entry.order_desc.contractInfo.exchange,
                                entry.order_desc.contractInfo.currency,
                                # Execution
                                entry.latest_execution.execId, entry.latest_execution.time, entry.latest_execution.avgPrice,
                                entry.latest_execution.side,
                                # Commission Report
                                entry.commission_report.commission, entry.commission_report.realizedPNL,
                                entry.commission_report.currency, entry.commission_report.yield_]
            writer.writerow(list_of_elements)
        
        self.last_id = self.last_id + 1
        return cur_id
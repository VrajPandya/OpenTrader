import json
import sys
from state_tracking.OrderSubscription import OrderDescriptor
from ibapi.commission_report import CommissionReport
from ibapi.execution import Execution

class FeeStructure:
    def __init__(self, fee_structure_json : str):
        self.fee_structure = json.loads(fee_structure_json)
    
    def get_fee(self, order_descriptor : OrderDescriptor) -> float:
        exchange = order_descriptor.contractInfo.primaryExchange
        symbol = order_descriptor.contractInfo.symbol + order_descriptor.contractInfo.currency

        cur_fee_struct = None
        if exchange in self.fee_structure and symbol in self.fee_structure[exchange]:
            cur_fee_struct = self.fee_structure[exchange][symbol]
        else:
            return sys.float_info.max

        if cur_fee_struct["structure"] == "OrderSize":
            return cur_fee_struct["fee"] * order_descriptor.currentAverageFillPrice * order_descriptor.orderInfo.filledQuantity
        else:
            return sys.float_info.max
        
    def get_currency(self, order_descriptor : OrderDescriptor) -> str:
        exchange = order_descriptor.contractInfo.primaryExchange
        symbol = order_descriptor.contractInfo.symbol

        cur_fee_struct = None
        if exchange in self.fee_structure and symbol in self.fee_structure[exchange]:
            cur_fee_struct = self.fee_structure[exchange][symbol]
        else:
            return "USD"

        return cur_fee_struct["currency"]
        
    def getCommissionReport(self, order_descriptor : OrderDescriptor):
        fee = self.get_fee(order_descriptor)
        commission_report = CommissionReport()
        commission_report.commission = fee
        commission_report.realizedPNL = 0
        commission_report.currency = "USD"
        return commission_report
    
    def getExecution(self, order_descriptor : OrderDescriptor):
        fee = self.get_fee(order_descriptor)
        exec = Execution()
        exec.side = "BOT" if order_descriptor.orderInfo.action == "BUY" else "SLD"
        exec.avgPrice = order_descriptor.currentAverageFillPrice
        exec.shares = order_descriptor.orderInfo.filledQuantity
        
        return exec

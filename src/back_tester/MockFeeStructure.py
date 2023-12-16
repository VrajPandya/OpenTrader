import json
import sys
from state_tracking.OrderSubscription import OrderDescriptor
from ibapi.commission_report import CommissionReport
from ibapi.execution import Execution

FEE_ROUNDING = 3

class FeeStructure:
    def __init__(self, fee_structure_json : str):
        with open(fee_structure_json) as fee_config_file:
            self.fee_structure = json.load(fee_config_file)
        
    
    def get_fee(self, order_descriptor : OrderDescriptor) -> float:
        exchange = order_descriptor.contractInfo.primaryExchange
        symbol = order_descriptor.contractInfo.symbol + order_descriptor.contractInfo.currency

        cur_fee_struct = None
        if exchange in self.fee_structure and symbol in self.fee_structure[exchange]:
            cur_fee_struct = self.fee_structure[exchange][symbol]
        else:
            return sys.float_info.max

        # Go through the fee structures and calculate the fee
        if cur_fee_struct["structure"] == "OrderSizeMultiple":
            return cur_fee_struct["fee_multiple"] * float(order_descriptor.currentAverageFillPrice) * float(order_descriptor.orderInfo.filledQuantity)
        else:
            return sys.float_info.max
        
    def get_currency(self, order_descriptor : OrderDescriptor) -> str:
        exchange = order_descriptor.contractInfo.primaryExchange
        symbol = order_descriptor.contractInfo.symbol

        if exchange in self.fee_structure and symbol in self.fee_structure[exchange]:
            return self.fee_structure[exchange][symbol]["currency"]
        else:
            return "USD"
        
    def getCommissionReport(self, order_descriptor : OrderDescriptor):
        commission_report = CommissionReport()
        commission_report.commission = round(self.get_fee(order_descriptor), FEE_ROUNDING)
        commission_report.realizedPNL = 0
        commission_report.currency = self.get_currency(order_descriptor)
        return commission_report
    
    def getExecution(self, order_descriptor : OrderDescriptor):
        exec = Execution()
        exec.side = "BOT" if order_descriptor.orderInfo.action == "BUY" else "SLD"
        exec.avgPrice = order_descriptor.currentAverageFillPrice
        exec.shares = order_descriptor.orderInfo.filledQuantity
        
        return exec

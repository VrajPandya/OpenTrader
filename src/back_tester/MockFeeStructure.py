import json
import sys
from state_tracking.OrderSubscription import OrderDescriptor

class FeeStructure:
    def __init__(self, fee_structure_json : str):
        self.fee_structure = json.loads(fee_structure_json)
    
    def get_fee(self, order_descriptor : OrderDescriptor) -> float:
        exchange = order_descriptor.contractInfo.primaryExchange
        symbol = order_descriptor.contractInfo.symbol

        cur_fee_struct = None
        if exchange in self.fee_structure and symbol in self.fee_structure[exchange]:
            cur_fee_struct = self.fee_structure[exchange][symbol]
        else:
            return sys.float_info.max

        if cur_fee_struct["structure"] == "OrderSize":
            return cur_fee_struct["fee"] * order_descriptor.currentAverageFillPrice * order_descriptor.orderInfo.filledQuantity
        else:
            return sys.float_info.max

from decimal import Decimal
from typing import Any 
from bson.codec_options import TypeCodec
from logic.ConstantStepOffsetTraderState import ConstantStepOffsetTraderState
from trader_mongo.TraderMongoInterface import MongoInterfaceManager, OrderInformationCodec
from state_tracking.OrderSubscription import OrderInformation
from trader_mongo.TraderMongoInterface import IBOrderCodec, IBContractCodec, OrderInformationCodec, DecimalCodec

class ConstantStepOffsetStateCodec(TypeCodec):
    python_type = ConstantStepOffsetTraderState
    bson_type = dict

    def transform_python(self, value):
        state_info = {}
        state_info["baseline"] = value.baseline
        state_info["stepDelta"] = value.stepDelta
        state_info["executionLimitOffset"] = value.executionLimitOffset
        state_info["stateTransitionThreshold"] = value.stateTransitionThreshold
        state_info["orderQuantityInUSD"] = value.orderQuantityInUSD
        result = {"state_info": state_info}
        return result

    def transform_bson(self, value):
        state_info = value["state_info"]
        result = ConstantStepOffsetTraderState()
        result.baseline = state_info["baseline"]
        result.stepDelta = state_info["stepDelta"]
        result.executionLimitOffset = state_info["executionLimitOffset"]
        result.stateTransitionThreshold = state_info["stateTransitionThreshold"]
        result.orderQuantityInUSD = state_info["orderQuantityInUSD"]
        
        return result
    
class ConstantStepOffsetExecutedOrderCodec(TypeCodec):
    python_type = list[list[OrderInformation], int, Decimal]
    bson_type = dict

    def __init__(self):
        super().__init__()
        self.order_information_codec = OrderInformationCodec()

    def transform_python(self, value):
        executed_order = {}
        executed_order["order_info"] = self.order_information_codec.transform_python(value[0])
        executed_order["execution_step"] = value[1]
        executed_order["baseline"] = value[2]
        result = {"executed_order": executed_order}
        return result
    
    def transform_bson(self, value):
        trade_state_info = value["executed_order"]
        result = [self.order_information_codec.transform_bson(trade_state_info["order_info"]),
                    trade_state_info["execution_step"],
                    trade_state_info["baseline"]]
        return result
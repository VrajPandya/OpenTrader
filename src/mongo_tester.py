from trader_mongo.TraderMongoInterface import MongoInterfaceManager, OrderDescriptorCodec
from state_tracking.OrderSubscription import OrderDescriptor
from ibkr_app.utils.contract_helper import createContractDescriptor
from ibkr_app.utils.order_helper import *
from decimal import Decimal, getcontext
from time import sleep
from bson.codec_options import TypeCodec, TypeRegistry, CodecOptions

# from logic.ConstantStepOffset import ConstantStepOffsetStateCodec, ConstantStepOffsetTraderState

class CustomTraderState:
    def __init__(self, order_info, execution_step, baseline):
        self.order_info = order_info
        self.execution_step = execution_step
        self.baseline = baseline

class CustomTraderCodec(TypeCodec):
    python_type = CustomTraderState
    bson_type = dict
    def __init__(self):
        super().__init__()
        self.order_descriptor_codec = OrderDescriptorCodec()

    def transform_python(self, value):
        result = {}
        result["order_info"] = self.order_descriptor_codec.transform_python(value.order_info)
        result["execution_step"] = value.execution_step
        result["baseline"] = value.baseline
        return result
    
    def transform_bson(self, value):
        # print(value)
        trade_state_info = value["executed_order"]
        result = CustomTraderState(self.order_descriptor_codec.transform_bson(trade_state_info["order_info"]),
                                   trade_state_info["execution_step"],
                                   trade_state_info["baseline"])
        return result

def main():
    getcontext().prec = 8
    btc_contract = createContractDescriptor("BTC", "CRYPTO", "USD", "SMART", "PAXOS")
    buy_quantity = Decimal('0.0001')
    targetPrice = Decimal('27000')
    order_desc = create_limit_order("BUY", "Minutes", buy_quantity, float(targetPrice))
    order_desc.orderId = 3

    order_to_add = OrderDescriptor(contract_info=btc_contract, order=order_desc)
    
    custom_trader_codec = CustomTraderCodec()
    type_registry = TypeRegistry([custom_trader_codec])
    
    trader_codec_options = CodecOptions(type_registry=type_registry)
    
    baseline = 32000

    execution_step = 5

    doc_to_push = CustomTraderState(order_to_add, execution_step, baseline)
    mongoInterfaceManager = MongoInterfaceManager()
    ## we passed the registry to the codec options 
    ## why no auto encode?
    collection = mongoInterfaceManager.getCollection("test_collection")
    
# insert one
    # mongoInterfaceManager.insert_one(collection, {"executed_order": custom_trader_codec.transform_python(doc_to_push)})
###

### update one
    write_result = mongoInterfaceManager.update_one(collection, 
        {"$set" : 
         {"executed_order.baseline": 34000}},
        {"$and" :
        [{"executed_order.baseline": 32000}, 
         {"executed_order.order_info.orderInfo.orderId" : 3},
         {"executed_order.execution_step" : 4}]})
    print(write_result)                  
###


### delete all documents with baseline 31000
    # response = collection.delete_many({"$and" :
    #         [{"executed_order.baseline": 31000}, 
    #          {"executed_order.order_info.orderInfo.orderId" : 3}]} )
    # print(str(response.deleted_count) + " documents deleted.")
###

### find many
    # cursor = collection.find({"executed_order.order_info.orderInfo.orderId": 3})
    cursor = collection.find({"$and": 
        [{"executed_order.baseline": 32000}, 
         {"executed_order.order_info.orderInfo.orderId" : 3},
         {"executed_order.execution_step" : 5}]})
    
    c1 = collection.find_one({"$and": 
        [{"executed_order.baseline": 32000}, 
         {"executed_order.order_info.orderInfo.orderId" : 3},
         {"executed_order.execution_step" : 5}]})

    print(c1['_id'])
    for document in cursor:
        custom_trade_state = custom_trader_codec.transform_bson(document)
        print("" + str(custom_trade_state.baseline) + " " + str(custom_trade_state.execution_step) + " mongo doc id" + str(document['_id']))
###

    # result = collection.find_one({"orderID": 1})
    # print(result)
    mongoInterfaceManager.my_q.join()

if __name__ == "__main__":
    main()
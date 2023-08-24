from pymongo import MongoClient
from threading import Thread
from decimal import Decimal
from queue import Queue

from ibapi.order import Order
from ibapi.contract import Contract
from ibapi.softdollartier import SoftDollarTier
from state_tracking.OrderSubscription import OrderInformation

# from bson.decimal128 import Decimal128
from bson.codec_options import TypeCodec
from bson.codec_options import TypeRegistry
from bson.codec_options import CodecOptions


MONGODB_NAME = "trader_test_db"
MONGODB_URL = "mongodb://localhost:27017/"

def IBDefaultBsonEncoder(obj):
    result = {}
    obj_dict = obj.__dict__
    for key in obj_dict:
        dict_val = obj_dict[key]
        if isinstance(dict_val, int) or isinstance(dict_val, str) \
        or isinstance(dict_val, float) or isinstance(dict_val, bool):
            result[key] = dict_val
        elif isinstance(dict_val, Decimal):
            temp = str(dict_val)
            result[key] = temp
        elif isinstance(dict_val, SoftDollarTier):
            result[key] = dict_val.__dict__
        elif isinstance(dict_val, type(None)):
            result[key] = None
        elif isinstance(dict_val, list):
            list_to_add = []
            for item in dict_val:
                list_to_add.append(IBDefaultBsonEncoder(item))
            result[key] = list_to_add
        else:
            # specially for the dict type
            raise TypeError("Unexpected type encountered in IBDefaultBsonEncoder")
    return result
    
# Function to decode a dictionary into an Order object
# Note: This function mutates the result object
def IBDefaultBsonDecoder(obj, result):
    # obj_dict = obj.__dict__
    ref_dict = result.__dict__
    for key in ref_dict:
        dict_val = obj[key]
        ref_val = ref_dict[key]
        if isinstance(ref_val, int) or isinstance(ref_val, str) \
        or isinstance(ref_val, float) or isinstance(ref_val, bool):
            setattr(result, key, dict_val)
        elif isinstance(ref_val, Decimal):
            setattr(result, key, Decimal(dict_val))
        elif isinstance(ref_val, SoftDollarTier):
            setattr(result, key, SoftDollarTier(**dict_val))
        elif isinstance(ref_val, type(None)):
            setattr(result, key, None)
        elif isinstance(ref_val, list):
            list_to_add = []
            for item in dict_val:
                list_to_add.append(IBDefaultBsonDecoder(item, ref_val[0]))
            setattr(result, key, list_to_add)
        else:
            # specially for the dict type
            raise TypeError("Unexpected type encountered in IBDefaultBsonDecoder")
        
        
class IBOrderCodec(TypeCodec):
    python_type = Order    # the Python type acted upon by this type codec
    bson_type = dict   # the BSON type acted upon by this type codec

    def transform_python(self, value):
        """Function that transforms a custom type value into a type
        that BSON can encode."""
        result = IBDefaultBsonEncoder(value)
        return result
            

    def transform_bson(self, value):
        """Function that transforms a vanilla BSON type value into our
        custom type."""
        result = Order()
        IBDefaultBsonDecoder(value, result)
        return result

class IBContractCodec(TypeCodec):
    python_type = Contract    # the Python type acted upon by this type codec
    bson_type = dict   # the BSON type acted upon by this type codec

    def transform_python(self, value):
        """Function that transforms a custom type value into a type
        that BSON can encode."""
        result = IBDefaultBsonEncoder(value)
        return result
    def transform_bson(self, value):
        """Function that transforms a vanilla BSON type value into our
        custom type."""
        result = Contract()
        IBDefaultBsonDecoder(value, result)
        return result

class OrderInformationCodec(TypeCodec):
    python_type = OrderInformation    # the Python type acted upon by this type codec
    bson_type = dict   # the BSON type acted upon by this type codec

    def __init__(self):
        super().__init__()
        self.contract_codec = IBContractCodec()
        self.order_codec = IBOrderCodec()
        self.decimal_codec = DecimalCodec()


    def transform_python(self, value):
        """Function that transforms a custom type value into a type
        that BSON can encode."""
        result = {}
        
        result["orderInfo"] = self.order_codec.transform_python(value.orderInfo)
        result["contractInfo"] = self.contract_codec.transform_python(value.contractInfo)
        result["ErrorState"] = value.errorState.__dict__
        return result
        
    def transform_bson(self, value):
        """Function that transforms a vanilla BSON type value into our
        custom type."""
        contract_info = self.contract_codec.transform_bson(value["contractInfo"])
        order_info = self.order_codec.transform_bson(value["orderInfo"])
        result = OrderInformation(contract_info=contract_info, order=order_info)
        error_state = value["ErrorState"]
        result.errorState = error_state
        return result

class DecimalCodec(TypeCodec):
    python_type = Decimal    # the Python type acted upon by this type codec
    bson_type = str   # the BSON type acted upon by this type codec
    def transform_python(self, value):
        """Function that transforms a custom type value into a type
        that BSON can encode."""
        return str(value)
    def transform_bson(self, value : str):
        """Function that transforms a vanilla BSON type value into our
        custom type."""
        return Decimal(value)

# Interface class for MongoDB
class MongoInterfaceManager(Thread):
    def __init__(self):
        super().__init__(daemon=True)
        
        self.client = MongoClient(MONGODB_URL)
        self.db = self.client[MONGODB_NAME]
        self.my_q = Queue()
        self.name = "MongoInterfaceManagerThread"
        self.start()

    def getCollection(self, collection_name, codec_options= None):
        return self.db.get_collection(collection_name, codec_options=codec_options)

    def run(self):
        while True:
            collection, document, opr = self.my_q.get()
            if opr == "insert_one":
                collection.insert_one(document)
            elif opr == "update_one":
                collection.
            elif opr == "delete_one":
                collection.delete_one(document)
            self.my_q.task_done()

    def insert_one(self,collection, document):
        self.my_q.put_nowait((collection, document, "insert_one"))
    
    def delete_one(self, collection, document):
        self.my_q.put_nowait((collection, document, "delete_one"))
        
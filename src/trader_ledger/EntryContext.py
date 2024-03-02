from bson.codec_options import TypeCodec

class EntryContext:
    def __init__(self):
        self.order_id = None
        self.entry_id = None

    def updateEntryID(self, entry_id):
        self.entry_id = entry_id
    
    def updateOrderID(self, order_id):
        self.order_id = order_id

class EntryContextCodec(TypeCodec):
    python_type = EntryContext
    bson_type = dict

    def transform_python(self, value : EntryContext):
        result = {}
        result["order_id"] = value.order_id
        result["entry_id"] = value.entry_id
        return result
    
    def transform_bson_for(self, obj_to_fill, value: dict):
        obj_to_fill.order_id = value["order_id"]
        obj_to_fill.entry_id = value["entry_id"]
        return obj_to_fill

    def transform_bson(self, value : dict):
        result = EntryContext()
        return self.transform_bson_for(result, value)

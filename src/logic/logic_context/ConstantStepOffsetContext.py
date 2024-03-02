from trader_ledger.EntryContext import EntryContext, EntryContextCodec
from bson.codec_options import TypeCodec

class ConstantStepOffsetContext():
    def __init__(self, baseline, step):
        self.entry_context = EntryContext()
        self.baseline = baseline
        self.step = step

    # TODO : Resolve the protocol issue
    # How do we extend a class / interface so that the new classes can
    # use the protocol methods but, don't inherit the class?
    def updateEntryID(self, entry_id):
        self.entry_context.updateEntryID(entry_id)
    
    def updateOrderID(self, order_id):
        self.entry_context.updateOrderID(order_id)

class ConstantStepOffsetContextCodec(TypeCodec):
    python_type = ConstantStepOffsetContext
    bson_type = dict

    def __init__(self):
        super().__init__()
        self.entry_context_codec = EntryContextCodec()

    def transform_python(self, value : ConstantStepOffsetContext):
        result = {}
        result["baseline"] = value.baseline
        result["step"] = value.step
        result["entry_context"] = self.entry_context_codec.transform_python(value.entry_context)
        return result
    
    def transform_bson(self, value : dict):
        result = ConstantStepOffsetContext(value["baseline"], value["step"])
        result.entry_context = self.entry_context_codec.transform_bson(value["entry_context"])
        return result
    
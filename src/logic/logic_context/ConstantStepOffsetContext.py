from trader_ledger.EntryContext import EntryContext
from bson.codec_options import TypeCodec

class ConstantStepOffsetContext(EntryContext):
    def __init__(self, entry_id, logic_context, 
                 baseline, offset):
        super().__init__(entry_id, logic_context)
        self.baseline = baseline
        self.offset = offset

class ConstantStepOffsetContextCodec(TypeCodec):
    python_type = ConstantStepOffsetContext
    bson_type = dict

    def transform_python(self, value):
        result = {}
        result["entry_id"] = value.entry_id
        result["logic_context"] = value.logic_context
        result["baseline"] = value.baseline
        result["offset"] = value.offset
        return result
    
    def transform_bson(self, value):
        result = ConstantStepOffsetContext(value["entry_id"], 
                                           value["logic_context"],
                                           value["baseline"],
                                           value["offset"])
        return result
class LedgerContextManager:
    def __init__(self, mongo_interface, context_codec,
                 collection_name):
        self.mongodb_interface = mongo_interface
        self.context_codec = context_codec
        self.collection_name = collection_name

    # NOTE: for now there can be only one context per entry_id
    def addContext(self, entry_id, context):
        document = self.context_codec.encode(context)
        context_lookup_query = {"$and":
            [{"entry_context.EntryID" : entry_id}]}
        self.mongodb_interface.find_one_and_replace(self.collection_name, 
                                                    document, context_lookup_query, upsert=True)
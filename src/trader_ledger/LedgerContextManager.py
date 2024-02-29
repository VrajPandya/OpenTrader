class LedgerContextManager:
    def __init__(self, mongo_interface):
        self.mongodb_interface = mongo_interface
        self.collection_name = None
        self.context_codec = None
        self.mongoCollection = None

    def updateContextCodec(self, context_codec):
        self.context_codec = context_codec

    def updateContextCollectionName(self, context_collection_name):
        self.collection_name = context_collection_name + "_context"
        self.mongoCollection = self.mongodb_interface.getCollection(context_collection_name)

    def addContext(self, context):
        document = self.context_codec.transform_python(context)
        self.mongodb_interface.insert_one(self.mongoCollection, document)
class EntryContext:
    def __init__(self, order_id, context_data):
        # Non serialized! 
        self.order_id = order_id
        
        # Serialized. 
        self.entry_id = None
        self.context_data = context_data

    def updateEntryID(self, entry_id):
        self.entry_id = entry_id

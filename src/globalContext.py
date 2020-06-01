class globalContext:
    def __init__(self):
        self.telegramNotificationsManager = None
        self.mongoInterfaceManager = None


GLOBAL_CONTEXT = globalContext()

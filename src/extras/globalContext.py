class globalContext:
    telegramNotificationsManager : TelegramNotificationsManager
    def __init__(self):
        self.telegramNotificationsManager = TelegramNotificationsManager()


GLOBAL_CONTEXT = globalContext()

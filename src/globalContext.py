from telegram_notifications.TelegramNotifications import TelegramNotificationsManager
from trader_mongo.TraderMongoInterface import MongoInterfaceManager

class globalContext:
    def __init__(self):
        self.telegramNotificationsManager = TelegramNotificationsManager()
        self.mongoInterfaceManager = MongoInterfaceManager()


GLOBAL_CONTEXT = globalContext()

from back_tester import MongoBackTester
from globalContext import GLOBAL_CONTEXT
from telegram_notifications.TelegramNotifications import TelegramNotificationsManagerStub
from logic.ConstantStepOffset import ConstantStepOffsetTrader
from trader_mongo.TraderMongoInterface import MongoInterfaceManager

CSV_DATA_PATH = "/Users/vrajpandya/repo/CryptoTrader/data/btc_historical_data_1.csv"

def main():
    global GLOBAL_CONTEXT
    GLOBAL_CONTEXT.telegramNotificationsManager = TelegramNotificationsManagerStub()
    GLOBAL_CONTEXT.mongoInterfaceManager = MongoInterfaceManager()
    backTester = MongoBackTester.BackTester(CSV_DATA_PATH, ConstantStepOffsetTrader())
    backTester.run()

if __name__ == "__main__":
    main()
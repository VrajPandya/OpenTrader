from back_tester import BackTester
from globalContext import GLOBAL_CONTEXT
from telegram_notifications.TelegramNotifications import TelegramNotificationsManagerStub
from logic.ConstantStepOffset import ConstantStepOffsetTrader
from trader_mongo.TraderMongoInterface import MongoInterfaceManager

CSV_DATA_PATH = "/Users/vrajpandya/repo/OpenTrader/data/btc_historical_data_1.csv"

def main():
    global GLOBAL_CONTEXT
    GLOBAL_CONTEXT.telegramNotificationsManager = TelegramNotificationsManagerStub()
    GLOBAL_CONTEXT.mongoInterfaceManager = MongoInterfaceManager()
    backTester = BackTester.BackTester(CSV_DATA_PATH, ConstantStepOffsetTrader("GEMINI"))
    backTester.run()

if __name__ == "__main__":
    main()
from telegram_notifications.TelegramNotifications import TelegramNotificationsManager
from ibkr_app.IBKRApp import IBKRApp
from logic.ConstantStepOffset import ConstantStepOffsetTrader
from ibkr_app.utils import app_setup
from globalContext import GLOBAL_CONTEXT
from trader_mongo.TraderMongoInterface import MongoInterfaceManager
from gemini_app.GeminiApp import GeminiApp

LOCAL_HOST = "127.0.0.1"


# setup data feed with
# data feed could be from IBKR or Gemini. It doesn't matter.
def setup_and_run_trading_app(app : IBKRApp, isPaper=False, logToConsole=False):
    
    app_setup.SetupLogger(logToConsole)
    
    import time
    time.sleep(1)
    app.bindAllLogic()
    app.start()

def setup_managers_and_globals():
    global GLOBAL_CONTEXT
    GLOBAL_CONTEXT.telegramNotificationsManager = TelegramNotificationsManager()
    GLOBAL_CONTEXT.mongoInterfaceManager = MongoInterfaceManager()

def gemini_trader_main():
    trader_logic_list = []
    
    setup_managers_and_globals()
    constantStepOffsetTrader = ConstantStepOffsetTrader()
    app = GeminiApp(trader_logic_list, is_paper=True)
    trader_logic_list.append(constantStepOffsetTrader)
    setup_and_run_trading_app(app)
    app.join()
    app.order_events_thread.join()

if __name__ == "__main__":
    gemini_trader_main()
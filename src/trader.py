from telegram_notifications.TelegramNotifications import TelegramNotificationsManager
from ibkr_app.IBKRApp import IBKRApp
from logic.ConstantStepOffset import ConstantStepOffsetTrader
from ibkr_app.utils import app_setup
from globalContext import GLOBAL_CONTEXT
from trader_mongo.TraderMongoInterface import MongoInterfaceManager
from gemini_app.GeminiApp import GeminiApp

TWS_PAPER_PORT = 7497
IBGATEWAY_PAPER_PORT = 4002

TWS_PROD_PORT = 7496
IBFATEWAY_PROD_PORT = 4001

LOCAL_HOST = "127.0.0.1"

#######################################################################
### IMP NOTE: DON't USE CLIENT ID 0
### Client ID 0 is for privilaged clients like TWS only
### Client 0 is able to reqest already placed orders
TRADER_BOT_CLIENT_ID = 5
#######################################################################


# setup data feed with
# data feed could be from IBKR or Gemini. It doesn't matter.
def setup_and_run_trading_app(app : IBKRApp, isPaper=False, logToConsole=False):
    
    app_setup.SetupLogger(logToConsole)
    
    app.reqIds(0)
    import time
    time.sleep(1)
    app.bindAllLogic()
    app.run()

def setup_managers_and_globals():
    global GLOBAL_CONTEXT
    GLOBAL_CONTEXT.telegramNotificationsManager = TelegramNotificationsManager()
    GLOBAL_CONTEXT.mongoInterfaceManager = MongoInterfaceManager()

def ib_trader_main():
    trader_logic_list = []
    
    setup_managers_and_globals()
    constantStepOffsetTrader = ConstantStepOffsetTrader()
    trader_logic_list.append(constantStepOffsetTrader)
    
    #TODO: make this configurable
    app = IBKRApp(trader_logic_list, isPaper=True)
    setup_and_run_trading_app(app)

if __name__ == "__main__":
    ib_trader_main()
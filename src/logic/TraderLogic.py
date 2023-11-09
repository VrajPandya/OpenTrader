from state_tracking.OrderSubscription import OrderSubscription
from state_tracking.PriceSubscription import PriceSubscription
from ibapi.commission_report import CommissionReport
from ibapi.execution import Execution
from ibkr_app.utils.TracingUtils import errorAndNotify
from ibapi.contract import Contract
from state_tracking.OrderSubscription import OrderDescriptor 
from telegram_notifications.TelegramNotifications import TelegramNotificationsManager
from pathlib import Path
import json
from os import listdir

###
###
### Trader Logic is a super class to all the logic.
### Trader Logic has enough protocol methods so that the core functions of trading
### e.g. price subscription / Order executions etc can be bridged and maintained
###
###

class TraderLogic(OrderSubscription, PriceSubscription):
    def getConfDir(self):
        # Keep it verbose for dev :-)
        source_path = Path(__file__).resolve()
        logic_dir = source_path.parent
        config_dir = logic_dir.joinpath(self.confDir) 
        return config_dir

    def getConfig(self, config_file_name : str):
        result = {}
        config_dir = self.getConfDir()
        logicConfigFilePath = config_dir.joinpath(config_file_name)
        with open(logicConfigFilePath) as config_file:
            result = json.load(config_file)
        return result
    
    def getConfigFiles(self, config_dir_name : str):
        conf_dir = self.getConfDir()
        return listdir(str(conf_dir))
        

    def __init__(self, contract_list: list[Contract]):
        PriceSubscription.__init__(self, contract_list)
        OrderSubscription.__init__(self)
        self.confDir = "TraderLogicConfigs"
        self.logicName = "NONE"

    def haltLogic(self):
        errorAndNotify("Halting the trader logic" + self.logicName)
        exit()

    def submitOrder(self, order_info):
        return self.orderAPI.placeOrderAndSubscribe(order_info, self)
    
    def setOrderAPI(self, order_api):
        self.orderAPI = order_api

    def unsetOrderAPI(self):
        self.orderAPI = None
    
    def onPriceUpdate(self, updated_price: float, contract_for_update: Contract):
        pass

    def onRejected(self, order_desc : OrderDescriptor):
        pass

    def onCanceled(self, order_desc : OrderDescriptor):
        pass

    def onAccepted(self, order_desc : OrderDescriptor):
        pass

    def onFilled(self, order_desc : OrderDescriptor):
        pass

    def onExecDetails(self, order_desc : OrderDescriptor, execution : Execution):
        pass

    def onCommissionReport(self, order_desc : OrderDescriptor, commission_report : CommissionReport):
        pass

    def saveState(self):
        pass

    def loadState(self):
        pass
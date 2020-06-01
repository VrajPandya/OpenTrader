from logic.TraderLogic import TraderLogic 
from ibkr_app.utils import contract_helper
from ibapi.contract import Contract
from enum import IntEnum, auto
from telegram_notifications.TelegramNotifications import TelegramNotificationsManager

class LogicState(IntEnum):
    baseline = auto()
    placedOrders = auto()


class DoubleDown(TraderLogic):
    # Traders have the logic to trade.
    def __init__(self, notification_manager : TelegramNotificationsManager):
        # Price subscription configuration 
        contract_list_to_subscribe = []
        btc_contract = contract_helper.createContractDescriptor("BTC", "CRYPTO", "USD", "SMART", "PAXOS")
        contract_list_to_subscribe.append(btc_contract)
        TraderLogic.__init__(self, contract_list_to_subscribe, notification_manager)

        # Trader logic state machine
        self.logicState = {}
        self.logicState[LogicState.baseline.value] = False
        self.baseline = 0.1
        self.executionThreshold = 50.0
        self.baselineThreshold = self.executionThreshold * 2
        self.OrderExecutionLoopState = "Long"

    def onPriceUpdate(self, updated_price : float, contract_descriptor: Contract):
        print("BTC Logic:" + str(updated_price) + str(Contract))
        ## Long Order Execution checks
        if updated_price < self.baseline - self.executionThreshold and not(self.already_bought):
            #Buy
            print("buy")
        if updated_price > self.baseline + self.executionThreshold and self.already_bought:
            # Sell
            print("sell")


        ## baseline Update checks
        if abs(self.baseline - updated_price) > self.baselineThreshold:
            self.baseline = updated_price 
    
    def onSubmitted(self, orderInfo):
        pass
    def onRejected(self, orderInfo):
        pass
    def onCanceled(self, orderInfo):
        pass
    def onAccepted(self, orderInfo):
        pass
    def onFilled(self, orderInfo):
        pass
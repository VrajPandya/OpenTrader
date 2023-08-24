from ibapi.contract import Contract
from ibkr_app.AppResponseErrorState import ErrorState
from ibapi.order import Order
from ibapi.order_state import OrderState
from decimal import Decimal
import logging

class OrderInformation:
    # All the state pertaining to the order!
    #
    # This contains both the states/values provided by IBKR API classes and
    # Some custom state information to ease and modularize implementation.
    #
    # This class also serves as an aggregate to all the data types 
    # provided by IBKR for an order e.g. Order, Error state etc.

    orderInfo : Order
    contractInfo: Contract
    errorState : ErrorState
    def __init__(self, contract_info : Contract, order: Order):
        self.orderID = -1
        
        # BUY or SELL action
        self.orderState = "CREATED_IN_LOGIC"
        self.contractInfo = contract_info
        self.orderInfo = order
        self.errorState = ErrorState()

        self.currentFill = Decimal("-0.1")
        self.currentRemaining = Decimal("-0.1")
        # so far we assume that we don't have negative price
        # TODO: implement negative price handlers
        # TODO: handle negative prices
        self.currentAverageFillPrice = -0.1
        self.lastFillPrice = -0.1
        self.whyHeld = ""
        self.marketCapPrice = -0.1
        self.IBKROrderState = OrderState()


class OrderSubscription:
    def __init__(self):
        return

    # def setOrderInterface(self, order_interface : IBKRApp):
    #     self.ibkrApp = order_interface

    # def submitOrder(self, orderInfo : OrderInformation):
    #     order_id = self.ibkrApp.placeOrder(orderInfo)
    #     logging.info(f"Submitted Order for orderID: " + order_id)
    #     return order_id

    def onSubmitted(self, order_info : OrderInformation):
        pass

    def onOrderOpened(self, order_info : OrderInformation):
        pass

    def onRejected(self, order_info : OrderInformation):
        #order_info.orderState = "REJECTED"
        pass

    def onCanceled(self, order_info : OrderInformation):
        pass

    def onAccepted(self, order_info : OrderInformation):
        pass

    def onFilled(self, order_info : OrderInformation):
        pass

    def onPartiallyFilled(self, order_info: OrderInformation):
        #order_info.orderState = "PARTIALLY_FILLED"
        pass

    def onInactive(self, order_info: OrderInformation):
        pass

    def onOrderError(self, order_info: OrderInformation):
        # TODO: handle cases where we have received the order staus
        # but not the error and all the permutations of the event chain
        # TODO: figure out the event chains.
        pass
###
### Lifecycle of the trade order
###
###    
###                               Create
###                                 |
###                                 V
###                  +------------Submited--------+
###                  |              |             |
###                  V              |             V
###       +-------Accepted----------+          Rejected
###       |          |              |
###       V          V              V
###   Partially    Filled         Canceled
###     Filled
###
###
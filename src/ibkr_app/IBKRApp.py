from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.utils import iswrapper
from ibapi.order_state import OrderState
from ibapi.commission_report import CommissionReport
from ibapi.execution import Execution
from ibapi import ticktype as IBTickType
from ibapi.order import Order

from state_tracking import Tracker
from state_tracking.OrderSubscription import OrderSubscription, OrderDescriptor
from ibkr_app.exception.StateMachineException import UnexpectedStateTransition
from ibkr_app.utils.TracingUtils import errorAndNotify, infoAndNotify

from logic.TraderLogic import TraderLogic
import logging
from decimal import getcontext, Decimal

import traceback

TWS_PAPER_PORT = 7497
IBGATEWAY_PAPER_PORT = 4002

TWS_PROD_PORT = 7496
IBGATEWAY_PROD_PORT = 4001

LOCAL_HOST = "127.0.0.1"

TRADER_BOT_CLIENT_ID = 5

class IBKRApp(EWrapper, EClient):
    def __init__(self, trader_logic_to_bind: list[TraderLogic], isPaper=True):
        EClient.__init__(self, self)
        self.nextValidOrderId = 1
        self.nKeybInt = 0
        self.done = False
        # for now an in memory/on disk open order list that was triggered by the bot
        self.orderTracker = Tracker.OrderTracker()
        # in memory price subscription tracker
        self.priceTracker = Tracker.PriceTracker()
        # in memory execution tracker OrderID<=>ExecutionID
        self.executionTracker = Tracker.ExecutionTracker()
        self.traderLogicList = trader_logic_to_bind
        
        # app_setup.SetupLogger()
        
        getcontext().prec = 8
        ib_port = TWS_PAPER_PORT if isPaper else TWS_PROD_PORT
        self.connect(LOCAL_HOST, ib_port, TRADER_BOT_CLIENT_ID)
        

    def bindAllLogic(self):
        for logic in self.traderLogicList:
            logic.setOrderAPI(self)
            self.bindContractSubscription(logic)

    def releaseAllLogic(self):
        # We call this to unsubscribe all the Price trackers and cancel all the orders that are in flight
        for logic in self.traderLogicList:
            self.releaseTraderLogic(logic)

    def releaseTraderLogic(self, logic):
        # TODO: Implement
        pass
        # logic.unsetOrderAPI()
        # self.unbindContractSubscription(logic)

    def bindContractSubscription(self, traderLogic: TraderLogic):
        for contract_descriptor in traderLogic.priceSubscriptionList:
            try:
                existingReqID = self.priceTracker.contractToRequestID[contract_descriptor]
                self.priceTracker.trackPriceSubscription(contract_descriptor, existingReqID, traderLogic)
                print (existingReqID)
            except KeyError:
                request_id = self.nextOrderId()
                print("requesting market data")
                self.reqMktData(request_id, contract_descriptor, '', False, False, [])
                # TODO : verify that the requested Market data stream is successfully opened
                self.priceTracker.trackPriceSubscription(contract_descriptor, request_id, traderLogic)

    def unbindContractSubscription(self, traderLogic: TraderLogic):
        pass
        # for contract_descriptor in traderLogic.priceSubscriptionList:
        #     try:
        #         request_id = self.priceTracker.contractToRequestID[contract_descriptor]
        #         self.cancelMktData(request_id)
        #         self.priceTracker.removePriceSubscription(contract_descriptor)
        #     except KeyError:
        #         print("KeyError: ", contract_descriptor)
        #         pass
                
    @iswrapper
    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson = ""):
        print("Contract Details: ", reqId, " ", errorCode, " ", errorString, " ")
        # find the order ID for which the error corresponds to
        order_subscriber = self.orderTracker.orderIDToSubscriber.get(reqId)
        
        logic_list = self.priceTracker.marketDataRequestIDToLogic.get(reqId)
        if reqId == -1:
            print("Error: ", reqId, " ", errorCode, " ", errorString, " ")
            return

        if logic_list != None:
            print (advancedOrderRejectJson)
            for logic in logic_list:
                logic.onOrderError
            return
        if order_subscriber != None:
            order_desc = self.orderTracker.orderIDToOrderDescriptor[reqId]
            order_subscriber.onCanceled(order_desc)
            return
        
        errorAndNotify("ERROR: " + errorString + " " + str(errorCode) + " " + str(reqId))
        

    
    @iswrapper
    def contractDetails(self, reqID: int, ContractDetails):
        logging.log(r"ContractDetails: " + reqID + " " + ContractDetails)

    @iswrapper
    def tickPrice(self, tickerId: int , tickType: IBTickType.TickType, price: float, attrib):
        super().tickPrice(tickerId, tickType, price, attrib)
        tick_contract = self.priceTracker.requestIDToContract[tickerId]
        logicInstancesToUpdate = self.priceTracker.marketDataRequestIDToLogic[tickerId]
        for logic in logicInstancesToUpdate:
            try:
                logic.onPriceUpdate(price, tick_contract)
            except UnexpectedStateTransition:
                logging.error("UnexpectedStateTransition!!! Stopping logic execution for: " + logic.logicName) 
                self.releaseTraderLogic(logic)

    @iswrapper
    def openOrder(self, orderID: int, contract: Contract, order: Order, orderState: OrderState):
        super().openOrder(orderID, contract, order, orderState)
        order_subscriber = self.orderTracker.orderIDToSubscriber[orderID]
        order_desc = self.orderTracker.orderIDToOrderDescriptor[orderID]
        order_desc.orderInfo = order
        order_desc.contractInfo = contract
        order_desc.IBKROrderState = orderState
        order_desc.orderState = "ORDER_OPENED"
        order_subscriber.onOrderOpened(order_desc)

    # Order status copied from https://interactivebrokers.github.io/tws-api/order_submission.html#order_status for IBAPI v 10.x
    # NOTE:  Often there are duplicate orderStatus messages.
    # ApiPending - indicates order has not yet been sent to IB server, for instance if there is a delay in receiving the security definition. Uncommonly received.
    # PendingSubmit - indicates the order was sent from TWS, but confirmation has not been received that it has been received by the destination. Most commonly because exchange is closed.
    # PendingCancel - indicates that a request has been sent to cancel an order but confirmation has not been received of its cancellation.
    # PreSubmitted - indicates that a simulated order type has been accepted by the IB system and that this order has yet to be elected. The order is held in the IB system until the election criteria are met. At that time the order is transmitted to the order destination as specified.
    # Submitted - indicates that your order has been accepted at the order destination and is working.
    # ApiCancelled - after an order has been submitted and before it has been acknowledged, an API client can request its cancellation, producing this state.
    # Cancelled - indicates that the balance of your order has been confirmed cancelled by the IB system. This could occur unexpectedly when IB or the destination has rejected your order. For example, if your order is subject to price checks, it could be cancelled, as explained in Order Placement Considerations
    # Filled - indicates that the order has been completely filled.
    # Inactive - indicates an order is not working, possible reasons include:
    # it is invalid or triggered an error. A corresponding error code is expected to the error() function.
    # This error may be a reject, for example a regulatory size reject. See Order Placement Considerations
    # the order is to short shares but the order is being held while shares are being located.
    # an order is placed manually in TWS while the exchange is closed.
    # an order is blocked by TWS due to a precautionary setting and appears there in an untransmitted state


    @iswrapper
    def orderStatus(self, orderID: int, status: str, filled: Decimal, remaining: Decimal, 
                    avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, 
                    clientId: int, whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderID, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        subscriber = self.orderTracker.orderIDToSubscriber[orderID]
        order_desc = self.orderTracker.orderIDToOrderDescriptor[orderID]
        order_desc.currentFill = filled
        order_desc.currentRemaining = remaining
        order_desc.currentAverageFillPrice = avgFillPrice
        order_desc.orderInfo.permId = permId
        order_desc.orderInfo.parentId = parentId
        order_desc.lastFillPrice = lastFillPrice
        order_desc.orderInfo.clientId = clientId
        order_desc.whyHeld = whyHeld
        order_desc.marketCapPrice = mktCapPrice
        ##################
        
        ##################
        # if status == "PreSubmitted":
        #     order_desc.orderState = "SUBMITTED"
        #     subscriber.onOrderOpened(order_desc)
        #     return
        if status == "Submitted" or status == "PreSubmitted":
            order_desc.orderState = "SUBMITTED"
            subscriber.onSubmitted(order_desc)
            return
        elif status == "ApiCancelled":
            order_desc.orderState = "CANCELED"
            subscriber.onCanceled(order_desc)
            return
        elif status == "Cancelled":
            order_desc.orderState = "CANCELED"
            subscriber.onCanceled(order_desc)
            return
        elif status == "Filled":
            order_desc.orderState = "FILLED"
            if remaining > 0:
                order_desc.orderState = "PARTIALLY_FILLED"
                subscriber.onPartiallyFilled(order_desc)
                return
            subscriber.onFilled(order_desc)
            return 
        elif status == "Inactive":
            order_desc.orderState = "INACTIVE"
            subscriber.onInactive(order_desc)
            return
        
        # We don't need to handle these order status
        if status == "ApiPending" or status == "PendingSubmit" or status == "PendingCancel":
            # So far I am not sure what more I can do here
            # Maybe log? but why? I can see the TWS.
            return


    ## IMP NOTE: the execution detail information SHOULD be overridable
    ## Based on the Property Discription of "Execution" class, 
    ## https://interactivebrokers.github.io/tws-api/classIBApi_1_1Execution.html
    ##
    ## Property of ExecID.
    ## 
    ## ======================================================================
    ##
    ## string 	ExecId [get, set]
    ##
 	## The execution's identifier. Each partial fill has a separate ExecId. 
    ## A correction is indicated by an ExecId which differs from a previous 
    ## ExecId in only the digits after the final period, e.g. an ExecId ending 
    ## in ".02" would be a correction of a previous execution with an ExecId 
    ## ending in ".01".
    ##
    ## ======================================================================
    ## 
    ## So, we should be fine maintaining only 1:1 mapping between orderID and
    ## latest executionID. 
    ## I.E. We will always override the executionID. Until proven otherwise.

    @iswrapper  
    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        super().execDetails(reqId, contract, execution)
        orderID = execution.orderId
        subscriber = self.orderTracker.orderIDToSubscriber[orderID]
        order_desc = self.orderTracker.orderIDToOrderDescriptor[orderID]

        self.executionTracker.trackExecution(execution, orderID)
        subscriber.onExecDetails(order_desc, execution)
        print("ExecDetails. ReqId:", reqId, "Symbol:", contract.symbol, "SecType:", contract.secType, "Currency:", contract.currency, execution)

    @iswrapper
    def commissionReport(self, commissionReport: CommissionReport):
        super().commissionReport(commissionReport)
        print("CommissionReport.", commissionReport)

    # this wrapper method will set the correct reqID in "self.nextValidOrderID"
    @iswrapper
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)

        logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId
        print("setting NextValidId:", orderId)

    ## basically we might have to call "nextValidID" when we start the 
    ## IBKR client App. Potentially.
    ## Per https://interactivebrokers.github.io/tws-api/classIBApi_1_1EClient.html#aecea365530f40e7b56529238c9dd2f4a
    ## i.e. built in reqIds() will get us the next request ID.
    ## we basically ask the server to get the the order id. 
    ## We need to call this method if the orderID we locally have 
    ## doesn't work and requests fail on invalid orderID. 
    ## Note: Keep track of the error state machine.
    ## TODO: Implement an error state machine.
     
    def nextOrderId(self) -> int:
        oid = self.nextValidOrderId
        self.nextValidOrderId += 1
        return oid

    def placeOrderAndSubscribe(self, order_descriptor : OrderDescriptor, order_subscription : OrderSubscription) -> int:
        order_id = self.nextOrderId()
        self.orderTracker.trackOrder(order_id, order_descriptor, order_subscription)
        self.placeOrder(order_id, order_descriptor.contractInfo, order_descriptor.orderInfo)
        order_descriptor.orderID = order_id
        return order_id
        
    def keyboardInterrupt(self, keyboard_int):
        self.nKeybInt += 1
        traceback.print_exception(keyboard_int) 
        print("how did we get here? why do we live?")
        if self.nKeybInt <= 5:
            self.stop()
        if self.nKeybIntHard > 5:
            self.stop()
            raise SystemExit()

    def cancelAllBuyOrders(self):
        #TODO: Implement this when we get more time.
        pass

    def orderOperations_cancel(self):
        print("canceling the orders")
        #self.cancelOrder(self.simplePlaceOid, "")
        #TODO finish the method

        # for now, we remove all the orders.
        self.reqGlobalCancel()


    def stop(self):
        print("Executing cancels")
        self.releaseAllLogic()
        self.orderOperations_cancel()
        self.disconnect()
        print("Executing cancels ... finished")

    def reqestContractDetails(self, contract_descriptor):
        orderID = self.nextOrderId()
        self.priceTracker.addOrder(orderID)
        self.reqContractDetails(orderID, contract_descriptor)

# We just hit circular dependancies
class OrderInterface:
    def __init__(self, ibkr_app : IBKRApp):
        self.ibkrApp = ibkr_app

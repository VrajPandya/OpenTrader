from logic.TraderLogic import TraderLogic 
from ibkr_app.utils import contract_helper, data_utils
from ibapi.contract import Contract
from ibkr_app.exception.StateMachineException import *
from ibkr_app.utils.order_helper import *
from decimal import Decimal
from ibkr_app.utils.TracingUtils import errorAndNotify, infoAndNotify
from globalContext import GLOBAL_CONTEXT
from state_tracking.OrderSubscription import OrderInformation
from trader_mongo import TraderMongoInterface
import logging

from logic.ConstantStepOffsetStateCodec import ConstantStepOffsetStateCodec, ConstantStepOffsetExecutedOrderCodec
from logic.ConstantStepOffsetTraderState import ConstantStepOffsetTraderState


class ConstantStepOffsetTrader(TraderLogic):
    def loadState(self):
        retrived_state_cursor = self.mongoCollection.find_one({"$and":
            [{"state_info.baseline" : self.state.baseline},
             {"state_info.stepDelta" : self.state.stepDelta},
             {"state_info.executionLimitOffset" : self.state.executionLimitOffset},
             {"state_info.stateTransitionThreshold" : self.state.stateTransitionThreshold},
             {"state_info.orderQuantityInUSD" : self.state.orderQuantityInUSD}]})
        if retrived_state_cursor is None:
            return
        # for document in retrived_state_cursor:
        #     self.state = self.stateCodec.transform_bson(document)
        #     break
        # else continue using the default state
        retrived_orders = self.mongoCollection.find({"executed_order.baseline" : self.state.baseline})
        if retrived_orders is None:
            return
        for document in retrived_orders:
            retrived_order = self.executedOrderCodec.transform_bson(document)
            self.state.executedOrders[retrived_order[1]] = retrived_order[0]

    def saveState(self):
        retrived_state_cursor = self.mongoCollection.find_one({"$and":
            [{"state_info.baseline" : self.state.baseline},
             {"state_info.stepDelta" : self.state.stepDelta},
             {"state_info.executionLimitOffset" : self.state.executionLimitOffset},
             {"state_info.stateTransitionThreshold" : self.state.stateTransitionThreshold},
             {"state_info.orderQuantityInUSD" : self.state.orderQuantityInUSD}]})
        if retrived_state_cursor is not None:
            return
        doc_to_insert = self.stateCodec.transform_python(self.state)
        self.monoInterfaceManager.insert_one(self.mongoCollection, doc_to_insert)

    def upsertExecutedOrderState(self, order_info: OrderInformation, orderStep: int):
        doc_to_insert = self.executedOrderCodec.transform_python([order_info, orderStep, self.state.baseline])
        self.monoInterfaceManager.insert_one(self.mongoCollection, doc_to_insert)


    def deleteExecutedOrder(self, order_info: OrderInformation, orderStep: int):
        response = self.monoInterfaceManager.delete_one(self.mongoCollection, { "$and" : [\
            {"executed_order.baseline" : self.state.baseline},\
            {"executed_order.execution_step": orderStep}\
            ]})
        if response == None:
            return
        logging.info("Deleted " + str(response.deleted_count) + " documents")

    def __init__(self):
        # PriceSubscriber 
        self.btc_contract = contract_helper.createContractDescriptor("BTC", "CRYPTO", "USD", "SMART", "PAXOS")
        TraderLogic.__init__(self, [self.btc_contract])
        self.executedOrderCodec = ConstantStepOffsetExecutedOrderCodec()
        self.stateCodec = ConstantStepOffsetStateCodec()
        # config members and what they do:
        # stepDelta: We execute BUY or sell on stepDelta. We BUY or SELL based on 
        #
        # executionLimitOffset: if the Current price of the instrument is 
        # higher than the Logic "baseline" by "executionLimitOffset", we don't put in new BUY orders.
        # we keep on putting/executing sell orders as the state machine allows.
        
        # Baseline: The baseline is the price at which we start the logic.
        # StateTransitionThreshold: The StateTransitionThreshold is the price at which we transition 
        # from "Observing" to "AboutToBuy" or "AboutToSell" state.

        # ExecutionLimitOffset: The ExecutionLimitOffset is the price at which we stop executing BUY and SELL orders.
        config_dir = self.getConfDir()
        self.config_file_name = "ConstantStepOffsetConfig.json"
        logic_file = config_dir.joinpath(self.config_file_name)
        self.state = ConstantStepOffsetTraderState()
        data_utils.dict_to_obj(self.getConfig(logic_file), self.state)
        # Trader logic state machine
        
        self.logicName = "ConstantStepOffset_Simple"
        self.monoInterfaceManager = GLOBAL_CONTEXT.mongoInterfaceManager
        self.mongoCollection = self.monoInterfaceManager.getCollection(self.logicName)

        self.orderQuantityInUSD = self.state.orderQuantityInUSD
        self.stateTransitionThreshold = self.state.stateTransitionThreshold
        self.executionLimitOffset = self.state.executionLimitOffset
        self.stepDelta = self.state.stepDelta
        self.maxSteps = (self.executionLimitOffset // self.stepDelta) - 1 
        self.state.executedOrders = []
        for i in range(0, self.maxSteps + 1):
            self.state.executedOrders.append(None)
        self.currentStep = 0

        # in memory state
        self.currentPrice = Decimal("0")
        self.previousPrice = Decimal("0")
        self.inFlightBuyOrders = []
        for i in range(0, self.maxSteps + 1):
            self.inFlightBuyOrders.append(None)

        self.inFlightSellOrders = []
        for i in range(0, self.maxSteps + 1):
            self.inFlightSellOrders.append(None)

        self.loadState()

    def priceIsGoingDown(self):
        return self.currentPrice < self.previousPrice

    def priceIsGoingUp(self):
        return self.currentPrice >= self.previousPrice
    
    def getOrderStep(self, order: OrderInformation):
        baseline = self.state.baseline
        stepDelta = self.stepDelta
        if order.orderInfo.action == "BUY":
            return int((baseline - order.orderInfo.lmtPrice) // stepDelta)
        else:
            return int((order.orderInfo.lmtPrice - baseline) // stepDelta)

    def placeBuyOrder(self, targetPrice: Decimal, buy_quantity: Decimal, cur_step : int):
        executedOrdersList = self.state.executedOrders
        inFlightBuyOrder = self.inFlightBuyOrders[cur_step]
        existing_order = executedOrdersList[cur_step]
        if ((existing_order != None) or (inFlightBuyOrder != None)):
            info_str = "Trying to place order for step " + str(cur_step) \
            + ". But the Order for that step has already been placed"
            logging.info(info_str)
            return
        buy_quantity = Decimal(buy_quantity).quantize(Decimal("0.00000001"))
        order_desc = create_limit_order("BUY", "Minutes", buy_quantity, float(targetPrice))
        order_information = OrderInformation(self.btc_contract, order_desc)
        self.state.logicState = "SubmittingOrder"
        self.inFlightBuyOrders[cur_step] = order_information
        self.submitOrder(order_information)
        
    def placeSellOrder(self, target_price: Decimal, sell_quantity: Decimal, cur_step: int):
        executedOrdersList = self.state.executedOrders
        inFlightSellOrder = self.inFlightSellOrders[cur_step]
        existing_order = executedOrdersList[cur_step]
        
        if ((existing_order == None) or (inFlightSellOrder != None)):
            info_str = "Trying to place sell order for step " + str(cur_step) \
            + ". But the Buy Order for that step has not yet placed."
            logging.info(info_str)
            return
        order_desc = create_limit_order("SELL", "Minutes", sell_quantity, float(target_price))
        order_information = OrderInformation(self.btc_contract, order_desc)
        self.state.logicState = "SubmittingOrder"
        self.inFlightSellOrders[cur_step] = order_information
        self.submitOrder(order_information)
        
    def reachedBuyZoneForStep(self) -> bool:
        baseline = self.state.baseline
        stepDelta = self.stepDelta
        executedOrdersList = self.state.executedOrders
        
        # check if we have already placed an order for this step
        already_placed_order = executedOrdersList[self.currentStep]
        if already_placed_order != None:
            # we have already placed and executed the ordered
            # keep on observing
            return False
        else: 
            # we need to place the order
            # here we go boys
            target_price = baseline - (stepDelta * self.currentStep)
            buy_zone_threshold = target_price + self.stateTransitionThreshold
            return self.currentPrice < buy_zone_threshold

    def reachedSellZoneForStep(self) -> bool:
        baseline = self.state.baseline
        stepDelta = self.stepDelta
        executedOrdersList = self.state.executedOrders
        
        
        already_placed_order = executedOrdersList[self.currentStep]
        if already_placed_order == None:
            # we have missed the oppertunity to buy or
            # we have already sold for the position
            # keep on observing
            return False
        else: 
            # we need to place the sell oppertunity order
            # here we go boys
            target_price = baseline + (stepDelta * self.currentStep)
            sell_zone_threshold = target_price + self.stateTransitionThreshold
            return self.currentPrice < sell_zone_threshold

    def transitionToAboutToBuyState(self):
        if self.state.logicState != "Observing":
            errorAndNotify("Transition to \'AboutToBuyState\' from \'"+ self.state.logicState + "\'State")
            raise UnexpectedStateTransition()
        self.state.logicState = "AboutToBuy"
    
    def transitionToAboutToSellState(self):
        if self.state.logicState != "Observing":
            errorAndNotify("Transition to \'AboutToSellState\' from \'"+ self.state.logicState + "\' State")
            raise UnexpectedStateTransition()
        self.state.logicState = "AboutToSell"

    def observe(self):
        if self.currentPrice < self.state.baseline:
            if self.reachedBuyZoneForStep():
                self.transitionToAboutToBuyState()
                return
        if self.currentPrice > self.state.baseline:
            if self.reachedSellZoneForStep():
                self.transitionToAboutToSellState()
                return
            
    def updatePriceStates(self, current_price):
        self.previousPrice = self.currentPrice
        self.currentPrice = current_price
        # calculate the current step
        if self.currentPrice > self.state.baseline:
            delta_price = self.currentPrice - self.state.baseline
        else:
            delta_price = self.state.baseline - self.currentPrice
        self.currentStep = int(delta_price // self.stepDelta)

        # TODO: Implement state transition to "UpdateBaseline" state

    def transitionToOvserveState(self):
        if self.state.logicState == "Observing":
            errorAndNotify("Transition to \'Observing\' State to \'Observing\' state")
        else:
            self.state.logicState = "Observing"

    def readyToBuy(self):
        if not(self.reachedBuyZoneForStep()):
            self.state.logicState = "Observing"
        # since this is a "readyToBuy" call, we assume that the 
        # current price will be lower than baseline

        baseline = self.state.baseline
        stepDelta = self.stepDelta

        target_price = baseline - (stepDelta * self.currentStep)

        if (target_price - self.currentPrice) < self.stateTransitionThreshold:
            buy_quantity = self.state.orderQuantityInUSD / self.currentPrice
            self.placeBuyOrder(target_price, buy_quantity, self.currentStep)
            

    
    def readyToSell(self):
        if not(self.reachedSellZoneForStep()):
            self.transitionToOvserveState()
        # since this is a "readyToSell" call, we assume that the 
        # current price will be higher than baseline

        baseline = self.state.baseline
        stepDelta = self.stepDelta
        executedOrders = self.state.executedOrders

        target_price = baseline + (stepDelta * self.currentStep)

        # since we are in "readyToSell" state we assume that the state transition from 
        # observation state has ensured that we actually have an executed buy order.
        # except in case we missed the oppertunity to buy
        placed_order_information = executedOrders[self.currentStep]

        if placed_order_information == None:
            # we missed the oppertunity to buy
            # transition to observation state
            self.transitionToOvserveState()
            return
        
        if (target_price - self.currentPrice) < self.stateTransitionThreshold:
            self.placeSellOrder(target_price, placed_order_information.orderInfo.totalQuantity, self.currentStep)


    def onPriceUpdate(self, updated_price : Decimal, contract_descriptor: Contract):
        currentStateOfLogic = self.state.logicState
        self.updatePriceStates(updated_price)

        ##### DEBUGGING #####
        if self.currentPrice > self.state.baseline:
            relative_to_baseline = "UP"
        else:
            relative_to_baseline = "DOWN"
        info_str = "CurrentPrice: " + str(self.currentPrice) + " Current Step: " \
              + str(self.currentStep) + " Current State: " + currentStateOfLogic \
              + " Relative to Baseline: " + relative_to_baseline
        print(info_str)
        logging.info(info_str)
        ##### DEBUGGING #####

        if self.currentStep > self.maxSteps or self.currentStep == 0:
            # Toe the line
            # Note: We shouldn't keep on buing and selling at step 0
            # since we will keep on buying and selling at the same price
            return 
        if currentStateOfLogic == "Observing":
            self.observe()
        elif currentStateOfLogic == "AboutToBuy":
            self.readyToBuy()
        elif currentStateOfLogic == "AboutToSell":
            self.readyToSell()
        elif currentStateOfLogic == "SubmittingOrder":
            return
        elif currentStateOfLogic == "UpdateBaseline":
            self.state.baseline = updated_price
            # We don't need to update the price states here
            # since the price states are updated in the next 
            # onPriceUpdate call
            infoAndNotify("Baseline Updated to " + str(updated_price))
        else:
            errorAndNotify("Reached Undefined state in OnPriceUpdate in ConstantOffset Update Logic")
            raise UnexpectedStateTransition()
        return
        
    def onSubmitted(self, order_info: OrderInformation):
        executedOrders = self.state.executedOrders
        orderStep = self.getOrderStep(order_info)
        executedOrderForStep = executedOrders[orderStep]
        action = order_info.orderInfo.action
        self.state.logicState = "Observing"
        if action == "BUY":
            if executedOrderForStep is None:
                # put Buy order in progress
                inProgressBuyOrderForStep = self.inFlightBuyOrders[orderStep]
                if inProgressBuyOrderForStep is not None:
                    # Order already in flight
                    return
                self.inFlightBuyOrders[orderStep] = order_info
        else :
            if executedOrderForStep is not None:
                # put sell order in progress
                inProgressSellOrderForStep = self.inFlightSellOrders[orderStep]
                if inProgressSellOrderForStep is not None:
                    # Order already in flight
                    return
                self.inFlightSellOrders[orderStep] = order_info
        self.saveExecutedOrderState(order_info, orderStep)
        return
        
    def onRejected(self, order_info: OrderInformation):
        inProgressOrderStep = self.getOrderStep(order_info)
        orderAction = order_info.orderInfo.action
        if orderAction == "BUY":
            self.inFlightBuyOrders[inProgressOrderStep] = None
            self.deleteExecutedOrder(order_info, inProgressOrderStep)
        else:
            self.inFlightSellOrders[inProgressOrderStep] = None
        if self.state.logicState == "SubmittingOrder":
            self.state.logicState = "Observing"
        infoAndNotify("Rejected " + order_info.orderInfo.action \
                       +"order! For Price: " + str(order_info.orderInfo.lmtPrice))
        
        
    def onCanceled(self, order_info: OrderInformation):
        inProgressOrderStep = self.getOrderStep(order_info)
        orderAction = order_info.orderInfo.action
        if orderAction == "BUY":
            self.inFlightBuyOrders[inProgressOrderStep] = None
            self.state.executedOrders[inProgressOrderStep] = None
            self.deleteExecutedOrder(order_info, inProgressOrderStep)
        else:
            self.inFlightSellOrders[inProgressOrderStep] = None
        if self.state.logicState == "SubmittingOrder":
            self.state.logicState = "Observing"
        infoAndNotify("Rejected " + order_info.orderInfo.action \
                       +"order! For Price: " + str(order_info.orderInfo.lmtPrice))
    
    ## FYI: On Accepted is called when the IBKR server accepts the order.
    ##      This does NOT mean that the order has been filled.
    def onAccepted(self, order_info: OrderInformation):
        return

    def onFilled(self, order_info: OrderInformation):
        order_action = order_info.orderInfo.action
        executed_orders = self.state.executedOrders

        inProgressOrderStep = self.getOrderStep(order_info)

        # We need to check if the order filled notification is duplicate or not.

        
        if order_action == "BUY":

            if self.inFlightBuyOrders[inProgressOrderStep] == None:
                # TODO: use order ID to ensure we are not deleting the wrong order
                # This is a duplicate notification
                return
            executed_orders[inProgressOrderStep] = order_info
            self.saveExecutedOrderState(order_info, inProgressOrderStep)
            self.inFlightBuyOrders[inProgressOrderStep] = None
        else:
            if self.inFlightSellOrders[inProgressOrderStep] == None:
                # TODO: use order ID to ensure we are not deleting the wrong order
                # This is a duplicate notification
                return
            executed_orders[inProgressOrderStep] = None
            self.inFlightSellOrders[inProgressOrderStep] = None
            self.deleteExecutedOrder(order_info, inProgressOrderStep)

        action_str = "BOUGHT" if order_action == "BUY" else "SOLD"
        infoAndNotify(action_str + "! Quatity: " + str(order_info.orderInfo.totalQuantity) +
                        " avgFillPrice: " + str(order_info.currentAverageFillPrice) +
                        " lastFillPrice: " + str(order_info.lastFillPrice))
        

    def onOrderError(self, order_info: OrderInformation):
        super().onOrderError(order_info)
        errorAndNotify("Something went Wrong:" + order_info.errorState.errorString + 
                       "Error Code:" + order_info.errorState.errorCode)
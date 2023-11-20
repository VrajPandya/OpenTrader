from state_tracking.OrderSubscription import OrderSubscription, OrderDescriptor
from ibapi.contract import Contract
from logic import TraderLogic
from ibapi.commission_report import CommissionReport
from ibapi.execution import Execution
import logging

### Order Tracker only tracks the orders that are Orders on an instrument.
### Order Tracker is an oracle that tracks all the Buy/Sell orders from
### all the Trader Logic.

### Note: OrderTracker doesn't handle price subscriptions.

class OrderTracker:
    orderIDToSubscriber : dict[int, OrderSubscription]
    orderIDToOrderDescriptor : dict[int, OrderDescriptor]

    def __init__(self):
        self.orderIDToSubscriber = dict()
        self.orderIDToOrderDescriptor = dict()

    def trackOrder(self, orderID: int, order_info :OrderDescriptor, subscriber :OrderSubscription):
        self.orderIDToSubscriber[orderID] = subscriber
        self.orderIDToOrderDescriptor[orderID] = order_info

    def stopTrackingOrder(self, orderID: int):
        removed_order = self.orderIDToSubscriber.pop(orderID, None)
        if removed_order == None:
            logging.error(f"Unexpected request to stop order Tracking for orderID: {orderID}")


### Price Tracker tracks the Price tracking subscriptions.
### Price Tracker is all in memory state management. 
### Since the configuration to which contracts to subscribe to should be defined in Trading Logic.

class PriceTracker:
    marketDataRequestIDToLogic : dict[int, list[TraderLogic.TraderLogic]]
    contractToRequestID : dict[Contract, int]
    requestIDToContract : dict[int, Contract]

    ## Geminit specific Tracker

    symbolToRequestID : dict[str, int]
    requestIDToSymbol : dict[int, str]

    def __init__(self):
        self.marketDataRequestIDToLogic = {}
        self.contractToRequestID = {}
        self.requestIDToContract = {}
        self.symbolToRequestID = {}
        self.requestIDToSymbol = {}

    def trackPriceSubscription(self, contract_descriptor: Contract, request_id : int, trader_logic : TraderLogic.TraderLogic):
        try:
            existing_list = self.marketDataRequestIDToLogic[request_id]
            existing_list.append(trader_logic)
        except KeyError:
            new_logic_list = []
            new_logic_list.append(trader_logic)
            symbol = contract_descriptor.symbol.upper() + contract_descriptor.currency.upper()
            self.symbolToRequestID[symbol] = request_id
            self.requestIDToSymbol[request_id] = symbol
            self.marketDataRequestIDToLogic[request_id] = new_logic_list
        
        self.contractToRequestID[contract_descriptor] = request_id
        self.requestIDToContract[request_id] = contract_descriptor

## IBKR Decides to send a number of "Executions" for single OrderID.
## IBKR Sends a single Commission Report for an Order.
## We need a way to track all the executions for a single orderID.
## Execution Tracker tracks all the executions for a single orderID.
## Execution ID to OrderID mapping is needed since,
## IBKR only sends Execution ID in the Commission Report.

class ExecutionTracker:
    executionIDToOrderID : dict[str, int]
    orderIDToExecutions : dict[int, list[Execution]]
    orderIDToCommissionReport : dict[int, CommissionReport]

    def __init__(self):
        self.executionIDToOrderID = dict()
        self.orderIDToExecutions = dict()
        self.orderIDToCommissionReport = dict()

    def trackExecution(self, execution: Execution, orderID: int):
        executionID = execution.execId
        self.executionIDToOrderID[executionID] = orderID
        try:
            existing_list = self.orderIDToExecutions[orderID]
            existing_list.append(execution)
        except KeyError:
            new_list = []
            new_list.append(execution)
            self.orderIDToExecutions[orderID] = new_list

    def trackCommissionReport(self, commission_report: CommissionReport, orderID: int):
        self.orderIDToCommissionReport[orderID] = commission_report

    def getExecutionsForOrderID(self, orderID: int):
        return self.orderIDToExecutions[orderID]

    def getCommissionReportForOrderID(self, orderID: int):
        return self.orderIDToCommissionReport[orderID]

    def getOrderIDForExecutionID(self, executionID: str):
        return self.executionIDToOrderID[executionID]

    def stopTrackingForOrderID(self, orderID: int):
        executions = self.orderIDToExecutions[orderID]
        self.orderIDToExecutions.pop(orderID, None)
        self.orderIDToCommissionReport.pop(orderID, None)
        for execution in executions:
            self.executionIDToOrderID.pop(execution.execId, None)

    def stopTrackingForExecutionID(self, executionID: str):
        self.executionIDToOrderID.pop(executionID, None)
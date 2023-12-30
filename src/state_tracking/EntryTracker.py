from ibapi.commission_report import CommissionReport
from ibapi.execution import Execution
from state_tracking.OrderSubscription import OrderDescriptor
from trader_ledger.Entry import Entry
from trader_ledger.EntryContext import EntryContext

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

class EntryTracker:
    orderIDToEntry : dict[int, Entry]

    def __init__(self):
        self.orderIDToEntry = dict()
        # cwd = getcwd()
        # self.ledgerManager = LedgerManager(output_path=cwd + "/data")
    
    def trackEntry(self, entry: Entry):
        orderID = entry.order_desc.orderID
        self.orderIDToEntry[orderID] = entry
    
    def updateEntryOrderDesc(self, orderID: int, order_desc: OrderDescriptor):
        entry = self.orderIDToEntry[orderID]
        entry.order_desc = order_desc

    def updateEntryLatestExecution(self, orderID: int, latest_execution: Execution):
        ## Getting Key error here.
        try:
            entry = self.orderIDToEntry[orderID]
        except KeyError:
            
        entry.latest_execution = latest_execution

    def updateEntryCommissionReport(self, orderID: int, commission_report: CommissionReport):
        entry = self.orderIDToEntry[orderID]
        entry.commission_report = commission_report

    def getEntryForOrderID(self, orderID: int):
        try:
            return self.orderIDToEntry[orderID]
        except KeyError:
            return None

    def stopTrackingForOrderID(self, orderID: int):
        self.orderIDToEntry.pop(orderID, None)

class EntryContextTracker:
    orderIDToEntryContext : dict[int, EntryContext]

    def __init__(self):
        self.orderIDToEntryContext = dict()
    
    def trackEntryContext(self, order_id: int, entry_context: EntryContext):
        self.orderIDToEntryContext[order_id] = entry_context

    def updateEntryContext(self, order_id: int, entry_context: EntryContext):
        self.orderIDToEntryContext[order_id] = entry_context
    
    def getEntryContextForOrderID(self, order_id: int):
        return self.orderIDToEntryContext[order_id]
    
    def stopTrackingForOrderID(self, order_id: int):
        self.orderIDToEntryContext.pop(order_id, None)
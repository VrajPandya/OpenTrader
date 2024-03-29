from state_tracking.OrderSubscription import OrderSubscription
from state_tracking.PriceSubscription import PriceSubscription
from state_tracking.EntryTracker import EntryTracker, EntryContextTracker
from ibapi.commission_report import CommissionReport
from ibapi.execution import Execution
from ibkr_app.utils.TracingUtils import errorAndNotify
from ibapi.contract import Contract
from globalContext import GLOBAL_CONTEXT
from state_tracking.OrderSubscription import OrderDescriptor 
from trader_ledger.LedgerManager import LedgerManager
from trader_ledger.Entry import Entry
from trader_ledger.LedgerContextManager import LedgerContextManager 
from trader_ledger.EntryContext import EntryContext

import json

from os import listdir, getcwd
from pathlib import Path
from threading import Lock


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
        self.executionLock = Lock()
        self.orderAPI = None
        self.entryTracker = EntryTracker()
        self.entryContextTracker = EntryContextTracker()
        cwd = getcwd()
        self.ledgerManager = LedgerManager(output_path=cwd + "/data")
        self.ledgerContextManager = LedgerContextManager(GLOBAL_CONTEXT.mongoInterfaceManager)
        
    def haltLogic(self):
        errorAndNotify("Halting the trader logic" + self.logicName)
        exit()

    # ===============================================================================================
    # It makes sense that when we submit the order we	should have all	the context we need.
    # So it makes sense to generate context there. So	we can	call SubmitOrder	with this context.
    # The TraderLogic	should be able to handle this.
    # We allow not generating	the context by setting the default value as well.
    # Generating Order and Entry context at the SubmitOrder handling avoids the need of maintaining
    # state of the context to	be transfered from the App logic to the	internal state machine,
    # later on. This also avoids need	for the	App to maintain	context	tracking.
    # This also helps	avoid the need to solve	the concurancy problem of populating Context into the
    # tracking state machine.
    # ===============================================================================================
    def submitOrder(self, order_desc, order_context = None):
        order_desc.orderID = self.orderAPI.placeOrderAndSubscribe(order_desc, self)
        if order_context != None:
            order_context.updateOrderID(order_desc.orderID)
            self.entryContextTracker.trackEntryContext(order_desc.orderID, order_context)
        self.entryTracker.trackEntry(Entry(order_desc, None, None, None)) 
        return order_desc.orderID
    
    def setOrderAPI(self, order_api):
        self.orderAPI = order_api

    def unsetOrderAPI(self):
        self.orderAPI = None
    
    def onPriceUpdate(self, updated_price : float, contract_descriptor: Contract):
        with self.executionLock:
            self.onPriceUpdateImpl(updated_price, contract_descriptor)
    
    def onRejected(self, order_desc: OrderDescriptor):
        with self.executionLock:
            self.entryTracker.stopTrackingForOrderID(order_desc.orderID)
            self.onRejectedImpl(order_desc)
            
    def onCanceled(self, order_desc: OrderDescriptor):
        with self.executionLock:
            self.entryTracker.stopTrackingForOrderID(order_desc.orderID)
            self.onCanceledImpl(order_desc)

    def onAccepted(self, order_desc: OrderDescriptor):
        with self.executionLock:
            self.onAcceptedImpl(order_desc)

    def onFilled(self, order_desc : OrderDescriptor):
        with self.executionLock:
            self.entryTracker.stopTrackingForOrderID(order_desc.orderID)
            self.onFilledImpl(order_desc)

    def considerWritingLedgerAndContext(self, order_desc : OrderDescriptor):
        entry_to_add = self.entryTracker.getEntryForOrderID(order_desc.orderID)
        if entry_to_add != None and entry_to_add.checkAllFeildsPresent():
            ledger_entry_id = self.ledgerManager.addEntry(entry_to_add)
            context = self.entryContextTracker.getEntryContextForOrderID(order_desc.orderID)
            context.updateEntryID(ledger_entry_id)
            self.ledgerContextManager.addContext(context)

    def onExecDetails(self, order_desc : OrderDescriptor, execution_report : Execution):
        with self.executionLock:
            self.entryTracker.updateEntryLatestExecution(order_desc.orderID, execution_report)
            # TODO: Need to verify if the Order Descriptor actually needs an update
            self.entryTracker.updateEntryOrderDesc(order_desc.orderID, order_desc)
            
            self.onExecDetailsImpl(order_desc, execution_report)
            
            self.considerWritingLedgerAndContext(order_desc)

            

    def onCommissionReport(self, order_desc : OrderDescriptor, commission_report : CommissionReport):
        with self.executionLock:
            self.entryTracker.updateEntryCommissionReport(order_desc.orderID, commission_report)
            # TODO: Need to verify if the Order Descriptor actually needs an update
            self.entryTracker.updateEntryOrderDesc(order_desc.orderID, order_desc)
            
            self.onCommissionReportImpl(order_desc, commission_report)
            
            self.considerWritingLedgerAndContext(order_desc)

    def onSubmitted(self, order_desc: OrderDescriptor):
        with self.executionLock:
            self.onSubmitterImpl(order_desc)

    def onOrderOpened(self, order_desc: OrderDescriptor):
        with self.executionLock:
            self.onOrderOpenedImpl(order_desc)

    def onOrderError(self, order_desc: OrderDescriptor):
        with self.executionLock:
            self.entryTracker.stopTrackingForOrderID(order_desc.orderID)
            self.onOrderErrorImpl(order_desc)

    def onPriceUpdateImpl(self, updated_price: float, contract_for_update: Contract):
        pass

    def onRejectedImpl(self, order_desc : OrderDescriptor):
        pass

    def onCanceledImpl(self, order_desc : OrderDescriptor):
        pass

    def onAcceptedImpl(self, order_desc : OrderDescriptor):
        pass

    def onFilledImpl(self, order_desc : OrderDescriptor):
        pass

    def onSubmitterImpl(self, order_desc: OrderDescriptor):
        pass

    def onOrderOpenedImpl(self, order_desc: OrderDescriptor):
        pass

    def onOrderErrorImpl(self, order_desc: OrderDescriptor):
        pass

    def onExecDetailsImpl(self, order_desc : OrderDescriptor, execution : Execution):
        pass

    def onCommissionReportImpl(self, order_desc : OrderDescriptor, commission_report : CommissionReport):
        pass

    def saveState(self):
        pass

    def loadState(self):
        pass

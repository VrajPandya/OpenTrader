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

    def submitOrder(self, order_desc):
        return self.orderAPI.placeOrderAndSubscribe(order_desc, self)
    
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
            self.entryTracker.trackEntry(Entry(order_desc, None, None, self.logicName))
            entry_context_data = self.onFilledImpl(order_desc)
            self.entryContextTracker.trackEntryContext(order_desc.orderID, 
                        EntryContext(order_desc.orderID, entry_context_data)) 

    def onExecDetails(self, order_desc : OrderDescriptor, execution_report : Execution):
        with self.executionLock:
            print("Exec Details : " + str(execution_report))
            self.entryTracker.updateEntryLatestExecution(order_desc.orderID, execution_report)
            self.onExecDetailsImpl(order_desc, execution_report)

            entry_to_add = self.entryTracker.getEntryForOrderID(order_desc.orderID)
            if entry_to_add != None and entry_to_add.checkAllFeildsPresent():
                self.ledgerManager.addEntry(entry_to_add)
                self.ledgerContextManager.addContext(entry_to_add, 
                                                     self.entryContextTracker.getEntryContextForOrderID(order_desc.orderID))

    def onCommissionReport(self, order_desc : OrderDescriptor, commission_report : CommissionReport):
        with self.executionLock:
            print("Commission Report : " + str(commission_report))
            self.entryTracker.updateEntryCommissionReport(order_desc.orderID, commission_report)
            context_data = self.onCommissionReportImpl(order_desc, commission_report)
            self.entryContextTracker.trackEntryContext(order_desc.orderID, EntryContext(-1, context_data))
            
            entry_to_add = self.entryTracker.getEntryForOrderID(order_desc.orderID)
            if entry_to_add != None and entry_to_add.checkAllFeildsPresent():
                self.ledgerManager.addEntry(entry_to_add)
                self.ledgerContextManager.addContext(entry_to_add, 
                                                     self.entryContextTracker.getEntryContextForOrderID(order_desc.orderID))

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

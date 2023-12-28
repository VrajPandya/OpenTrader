from state_tracking.OrderSubscription import OrderDescriptor
from ibapi.execution import Execution
from ibapi.commission_report import CommissionReport
class Entry:
    def __init__(self, order_desc : OrderDescriptor, latest_execution : Execution, 
                 commission_report : CommissionReport, logic_name : str):
        self.order_desc = order_desc
        self.latest_execution = latest_execution
        self.commission_report = commission_report
        self.logic_name = logic_name

    def checkAllFeildsPresent(self):
        if self.order_desc == None or self.latest_execution == None \
        or self.commission_report == None:
            return False
        return True


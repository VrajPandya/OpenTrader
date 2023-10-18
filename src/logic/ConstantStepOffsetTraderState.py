from decimal import Decimal

class ConstantStepOffsetTraderState:
    def __init__(self):
        self.baseline = Decimal(0.0)
        self.stepDelta = 0
        self.executionLimitOffset = Decimal(0.0)
        self.stateTransitionThreshold = Decimal(0.0)
        self.orderQuantityInUSD = Decimal(0.0)
        self.logicState = "Observing"
        self.executedOrders = []
        

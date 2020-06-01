class ConstantStepOffsetTraderState:
    def __init__(self):
        self.baseline = 0.0
        self.stepDelta = 0
        self.executionLimitOffset = 0.0
        self.stateTransitionThreshold = 0
        self.orderQuantityInUSD = 0.0
        self.logicState = "Observing"
        self.executedOrders = []
        

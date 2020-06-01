class ErrorState:
    def __init__(self, order_id = -1, error_code = -111, 
                 error_str = "", advanced_order_reject = {}):
        self.orderID = order_id
        self.errorCode = error_code
        self.errorString = error_str
        self.advancedOrderReject = advanced_order_reject
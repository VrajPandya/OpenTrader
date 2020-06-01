class OrderTrackerException(Exception):
    pass

class ExisitingOrderError(OrderTrackerException):
    pass
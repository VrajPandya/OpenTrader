from ibapi.order import Order

from decimal import Decimal

def create_limit_order(order_action: str, tif: str, 
                        order_quantity: Decimal, 
                        order_price: float):
    order = Order()
    order.action = order_action
    order.orderType = "LMT"
    order.tif = tif
    # order.outsideRth = True
    order.totalQuantity = order_quantity
    order.lmtPrice = order_price
    return order
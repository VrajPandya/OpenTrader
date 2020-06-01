from ibapi.contract import Contract
from ibkr_app.AppResponseErrorState import ErrorState

class PriceSubscription:
    priceSubscriptionList: list[Contract]
    ###
    ###
    ### Price Subscription: A Program logic can subscribe to a set of Ticker prices.
    ### Price Subscription is a data class that help bridge the information between Trading logic 
    ### and the IBKR App/data service.
    ### 
    ###
    def __init__(self, contract_list : list[Contract]):
        # list  of contracts to subscribe to
        
        self.priceSubscriptionList  = contract_list
    
    def onPriceUpdate(self, updated_price: float, contract : Contract):
        pass

    def onPriceSubscriptionError(self, error_state : ErrorState):
        pass
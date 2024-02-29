import websocket, ssl, base64, logging, json, hmac, hashlib, time, requests
from ibapi.contract import Contract
from ibapi.order_state import OrderState
from ibapi import ticktype as IBTickType
from ibapi.order import Order

from state_tracking import Tracker
from state_tracking.OrderSubscription import OrderSubscription, OrderDescriptor
from ibkr_app.exception.StateMachineException import UnexpectedStateTransition
from ibkr_app.utils.TracingUtils import errorAndNotify, infoAndNotify

from logic.TraderLogic import TraderLogic
from decimal import getcontext, Decimal
from threading import Thread
from logic.TraderLogic import TraderLogic
from pathlib import Path

USER_HOME = str(Path.home())
GEMINI_API_KEY_PATH = USER_HOME + "/.ssh/stars_in_sky.txt"

GEMINI_API_SECRET_PATH = USER_HOME + "/.ssh/stars_aligned"

PING_INTERVAL = 30

class GeminiApp(Thread):
    def __init__(self, trader_logic_to_bind: list[TraderLogic], is_paper : bool) -> None:
        Thread.__init__(self, name="GeminiApp")
        self.nextValidOrderId = 1
        self.nKeybInt = 0
        self.isPaper = is_paper
        # for now an in memory/on disk open order list that was triggered by the bot
        self.orderTracker = Tracker.OrderTracker()
        # in memory price subscription tracker
        self.priceTracker = Tracker.PriceTracker()
        self.traderLogicList = trader_logic_to_bind
        self.name = "GeminiApp"
        self.gemini_api_key = ""
        self.gemini_api_secret = ""
        self.done = False
        with open(GEMINI_API_KEY_PATH, "r") as f:
            self.gemini_api_key = f.readline().strip()

        with open(GEMINI_API_SECRET_PATH, "r") as f:
            self.gemini_api_secret = f.readline().strip().encode()
        
        self.webSocketsToRun = []
        
        getcontext().prec = 8
        self.order_events_thread = Thread(target=self.order_events_loop, name="OrderEventsThread")
        self.order_events_thread.start()

    def order_events_loop(self):
        payload = {"request": "/v1/order/events","nonce": time.time()}
        encoded_payload = json.dumps(payload).encode()
        b64 = base64.b64encode(encoded_payload)
        signature = hmac.new(self.gemini_api_secret, b64, hashlib.sha384).hexdigest()

        gemini_url = "wss://api.gemini.com/v1/order/events"
        if self.isPaper:
            gemini_url = "wss://api.sandbox.gemini.com/v1/order/events"
        ws = websocket.WebSocketApp(gemini_url,
            on_message=self.on_order_event,
            on_error=self.on_order_error_event,
            header={
                'X-GEMINI-PAYLOAD': b64.decode(),
                'X-GEMINI-APIKEY': self.gemini_api_key,
                'X-GEMINI-SIGNATURE': signature
            })
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=PING_INTERVAL)

    def on_order_error_event(self, ws, error):
        print("Order Event Error:")
        print(error)

    def on_order_event(self, ws, message):
        response = json.loads(message)
        if isinstance(response, dict):
            type = response["type"]
            if type == "heartbeat" or type == "subscription_ack":
                return
            else:
                raise Exception("unexpected order event type: " + type)
        for message_dict in response:
            try:
                type = message_dict["type"]
                internal_status_type = ""
                print(message)
                ## convert Gemini lingo to internal
                if type == "heartbeat" or type == "subscription_ack":
                    return
                elif type == "initial":
                    internal_status_type = "ORDER_OPENED"
                elif type == "accepted" or type == "booked":
                    internal_status_type = "Submitted"
                elif type == "fill":
                    internal_status_type = "Filled"
                elif type == "cancelled" or type == "cancel_rejected" or type == "rejected":
                    internal_status_type = "Cancelled"
                else:
                    raise Exception("Unknown order event type: " + type)
                executed_amount = Decimal('0')
                remaining_amount = Decimal('0')
                avg_execution_price = 0.0
                last_fill_price = 0.0
                reason = ""
                try:
                    executed_amount = Decimal(message_dict["executed_amount"])
                    remaining_amount = Decimal(message_dict["remaining_amount"])
                    avg_execution_price = float(message_dict["avg_execution_price"])
                    last_fill_price = float(message_dict["price"])
                    reason = message_dict["reason"]
                except KeyError:
                    pass
                self.orderStatus(orderID=int(message_dict["client_order_id"]),
                                status=internal_status_type,
                                filled=executed_amount,
                                remaining=remaining_amount,
                                avgFillPrice=avg_execution_price,
                                permId=int(message_dict["order_id"]),
                                parentId= 0,
                                lastFillPrice=last_fill_price,
                                clientId=message_dict["api_session"],
                                whyHeld=reason,
                                mktCapPrice=0)
            except Exception as e:
                print("Error parsing order event: " + str(e))
                print(message_dict)
        print(message)

    def run(self):
        self.webSocketsToRun[0].run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=PING_INTERVAL)

    def bindAllLogic(self):
        for logic in self.traderLogicList:
            logic.setOrderAPI(self)
            self.bindContractSubscription(logic)

    def releaseTraderLogic(self, logic):
        # TODO: Implement
        pass

    def releaseAllLogic(self):
        # We call this to unsubscribe all the Price trackers and cancel all the orders that are in flight
        for logic in self.traderLogicList:
            self.releaseTraderLogic(logic)
    
    def send_sub_request(self, ws):
        candle_sub_msg ='{ "type": "subscribe","subscriptions": [{"name": "l2","symbols": ["BTCUSD"]}]}'
        ws.send(candle_sub_msg)

    def startMarketDataStream(self, reqID: int, contract: Contract):
        gemini_url= "wss://api.gemini.com/v1/marketdata/btcusd?trades=true&top_of_book=true&bids=true&offers=false"
        if self.isPaper:
            gemini_url = "wss://api.sandbox.gemini.com/v1/marketdata/btcusd?trades=true&top_of_book=true&bids=true&offers=false"
        websocket_url = gemini_url + contract.symbol + contract.currency
        ws = websocket.WebSocketApp(
            websocket_url,
            on_message=self.tickPrice,
            on_error=self.error,
            on_close=self.onMarketDataSocketClose,
            on_open=self.send_sub_request)
        self.webSocketsToRun.append(ws)

    def bindContractSubscription(self, traderLogic: TraderLogic):
        for contract_descriptor in traderLogic.priceSubscriptionList:
            try:
                existingReqID = self.priceTracker.contractToRequestID[contract_descriptor]
                self.priceTracker.trackPriceSubscription(contract_descriptor, existingReqID, traderLogic)
                print (existingReqID)
            except KeyError:
                request_id = self.nextOrderId()
                print("requesting market data")
                self.startMarketDataStream(request_id, contract_descriptor)
                # TODO : write logic in a way we can verify that the requested Market data stream is successfully opened
                self.priceTracker.trackPriceSubscription(contract_descriptor, request_id, traderLogic)
                
    def error(self, ws, message):
        print(message)

    def onMarketDataSocketClose(self, ws):
        if self.done:
            return
        self.webSocketsToRun[0].run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def tickPrice(self, ws, message):
        message_dict = json.loads(message, parse_float=Decimal)
        type = message_dict["type"]
        if type == "heartbeat":
            return
        # print(message)
        # print (type)
        if type == "update":
            for event in message_dict["events"]:
                # symbol = event["symbol"]
                symbol = "BTCUSD"
                price = float(event["price"])
                
                # print (reason)
                # if reason == "trade":
                tickerId = self.priceTracker.symbolToRequestID[symbol]
                tick_contract = self.priceTracker.requestIDToContract[tickerId]
                logicInstancesToUpdate = self.priceTracker.marketDataRequestIDToLogic[tickerId]
                for logic in logicInstancesToUpdate:
                    try:
                        logic.onPriceUpdate(price, tick_contract)
                        print(message_dict["socket_sequence"])
                    except UnexpectedStateTransition:
                        logging.error("UnexpectedStateTransition!!! Stopping logic execution for: " + logic.logicName) 
                        self.releaseTraderLogic(logic)

    def openOrder(self, orderID: int, contract: Contract, order: Order, orderState: OrderState):
        super().openOrder(orderID, contract, order, orderState)
        order_subscriber = self.orderTracker.orderIDToSubscriber[orderID]
        order_info = self.orderTracker.orderIDToOrderDescriptor[orderID]
        order_info.orderInfo = order
        order_info.contractInfo = contract
        order_info.IBKROrderState = orderState
        order_info.orderState = "ORDER_OPENED"
        order_subscriber.onOrderOpened(order_info)

    # Order status copied from https://interactivebrokers.github.io/tws-api/order_submission.html#order_status for IBAPI v 10.x
    # NOTE:  Often there are duplicate orderStatus messages.
    # ApiPending - indicates order has not yet been sent to IB server, for instance if there is a delay in receiving the security definition. Uncommonly received.
    # PendingSubmit - indicates the order was sent from TWS, but confirmation has not been received that it has been received by the destination. Most commonly because exchange is closed.
    # PendingCancel - indicates that a request has been sent to cancel an order but confirmation has not been received of its cancellation.
    # PreSubmitted - indicates that a simulated order type has been accepted by the IB system and that this order has yet to be elected. The order is held in the IB system until the election criteria are met. At that time the order is transmitted to the order destination as specified.
    # Submitted - indicates that your order has been accepted at the order destination and is working.
    # ApiCancelled - after an order has been submitted and before it has been acknowledged, an API client can request its cancellation, producing this state.
    # Cancelled - indicates that the balance of your order has been confirmed cancelled by the IB system. This could occur unexpectedly when IB or the destination has rejected your order. For example, if your order is subject to price checks, it could be cancelled, as explained in Order Placement Considerations
    # Filled - indicates that the order has been completely filled.
    # Inactive - indicates an order is not working, possible reasons include:
    # it is invalid or triggered an error. A corresponding error code is expected to the error() function.
    # This error may be a reject, for example a regulatory size reject. See Order Placement Considerations
    # the order is to short shares but the order is being held while shares are being located.
    # an order is placed manually in TWS while the exchange is closed.
    # an order is blocked by TWS due to a precautionary setting and appears there in an untransmitted state


    def orderStatus(self, orderID: int, status: str, filled: Decimal, remaining: Decimal, 
                    avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, 
                    clientId: str, whyHeld: str, mktCapPrice: float):
        subscriber = self.orderTracker.orderIDToSubscriber[orderID]
        order_info = self.orderTracker.orderIDToOrderDescriptor[orderID]
        order_info.currentFill = filled
        order_info.currentRemaining = remaining
        order_info.currentAverageFillPrice = avgFillPrice
        order_info.orderInfo.permId = permId
        order_info.orderInfo.parentId = parentId
        order_info.lastFillPrice = lastFillPrice
        order_info.orderInfo.clientId = clientId
        order_info.whyHeld = whyHeld
        order_info.marketCapPrice = mktCapPrice
        order_info.orderState = status
        ##################
        
        ##################
        if status == "ORDER_OPENED":
            order_info.orderState = "ORDER_OPENED"
            subscriber.onOrderOpened(order_info)
            return
        if status == "Submitted" or status == "PreSubmitted":
            order_info.orderState = "SUBMITTED"
            subscriber.onSubmitted(order_info)
            return
        elif status == "ApiCancelled":
            order_info.orderState = "CANCELED"
            subscriber.onCanceled(order_info)
            return
        elif status == "Cancelled":
            order_info.orderState = "CANCELED"
            subscriber.onCanceled(order_info)
            return
        elif status == "Filled":
            order_info.orderState = "FILLED"
            if remaining > 0:
                order_info.orderState = "PARTIALLY_FILLED"
                subscriber.onPartiallyFilled(order_info)
                return
            subscriber.onFilled(order_info)
            return 
        elif status == "Inactive":
            order_info.orderState = "INACTIVE"
            subscriber.onInactive(order_info)
            return
        
        # We don't need to handle these order status
        if status == "ApiPending" or status == "PendingSubmit" or status == "PendingCancel":
            # So far I am not sure what more I can do here
            # Maybe log? but why? I can see the TWS.
            return
                

    # this wrapper method will set the correct reqID in "self.nextValidOrderID"
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)

        logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId
        print("setting NextValidId:", oxrderId)

    ## basically we might have to call "nextValidID" when we start the 
    ## IBKR client App. Potentially.
    ## Per https://interactivebrokers.github.io/tws-api/classIBApi_1_1EClient.html#aecea365530f40e7b56529238c9dd2f4a
    ## i.e. built in reqIds() will get us the next request ID.
    ## we basically ask the server to get the the order id. 
    ## We need to call this method if the orderID we locally have 
    ## doesn't work and requests fail on invalid orderID. 
    ## Note: Kepp track of the error state machine.
    ## TODO: Implement an error state machine.
     
    def nextOrderId(self) -> int:
        oid = self.nextValidOrderId
        self.nextValidOrderId += 1
        return oid
    
    def placeGeminiOrder(self, orderID: int, contract: Contract, order: Order):
        base_url = "https://api.gemini.com"
        if self.isPaper:
            base_url = "https://api.sandbox.gemini.com"
        endpoint = "/v1/order/new"
        url = base_url + endpoint

        payload_nonce = time.time()
        payload = {
        "request": "/v1/order/new",
        "nonce": payload_nonce,
        "client_order_id": str(orderID),
        "symbol": contract.symbol + contract.currency,
        "amount": float(order.totalQuantity),
        "price": float(order.lmtPrice),
        "side": order.action.lower(),
        "type": "exchange limit",
        "options": [] 
        }
        encoded_payload = json.dumps(payload).encode()
        b64 = base64.b64encode(encoded_payload)
        signature = hmac.new(self.gemini_api_secret, b64, hashlib.sha384).hexdigest()

        request_headers = { 'Content-Type': "text/plain",
                    'Content-Length': "0",
                    'X-GEMINI-APIKEY': self.gemini_api_key,
                    'X-GEMINI-PAYLOAD': b64,
                    'X-GEMINI-SIGNATURE': signature,
                    'Cache-Control': "no-cache" }

        response = requests.post(url,
                        data=None,
                        headers=request_headers)

        new_order = response.json()


    def placeOrderAndSubscribe(self, order_descriptor : OrderDescriptor, order_subscription : OrderSubscription) -> int:
        order_id = self.nextOrderId()
        self.orderTracker.trackOrder(order_id, order_descriptor, order_subscription)
        self.placeGeminiOrder(order_id, order_descriptor.contractInfo, order_descriptor.orderInfo)
        order_descriptor.orderID = order_id
        return order_id
        
    def keyboardInterrupt(self, keyboard_int):
        self.nKeybInt += 1
        traceback.print_exception(keyboard_int) 
        print("how did we get here? why do we live?")
        if self.nKeybInt <= 5:
            self.stop()
        if self.nKeybInt > 5:
            self.stop()
            raise SystemExit()

    def cancelAllBuyOrders(self):
        #TODO: Implement this when we get more time.
        pass

    def orderOperations_cancel(self):
        print("canceling the orders")
        #self.cancelOrder(self.simplePlaceOid, "")
        #TODO finish the method

        # for now, we remove all the orders.
        self.reqGlobalCancel()


    def stop(self):
        self.done = True
        print("Executing cancels")
        self.releaseAllLogic()
        self.orderOperations_cancel()
        self.disconnect()
        print("Executing cancels ... finished")

    def reqestContractDetails(self, contract_descriptor):
        orderID = self.nextOrderId()
        self.priceTracker.addOrder(orderID)
        self.reqContractDetails(orderID, contract_descriptor)

# We just hit circular dependancies
class OrderInterface:
    def __init__(self, app : GeminiApp):
        self.ibkrApp = app

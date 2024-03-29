import csv
from decimal import Decimal
from logic.TraderLogic import TraderLogic
from state_tracking.OrderSubscription import OrderDescriptor
from ibkr_app.utils.TracingUtils import errorAndNotify
from ibkr_app.utils.contract_helper import createContractDescriptor
import matplotlib.pyplot as plt
from back_tester.MockFeeStructure import FeeStructure

BTC_CONTRACT = createContractDescriptor("BTC", "CRYPTO", "USD", "SMART", "GEMINI")
FEE_STRUCTURE_JSON = "fee_structure.json"

class BackTester:
    def __init__(self, csv_data_path : str, strategy : TraderLogic):
        self.csv_data_path = csv_data_path
        self.strategy = strategy
        self.openOrders = []
        self.executedOrders = []
        self.inFlightOrders = []
        self.currentTickTime = 0
        self.curBackTestOrderID = 0 
        self.currentTick = 0
        self.currentExecutionID = 0
        self.feeStructure = FeeStructure("src/back_tester/default_fees.json")
        self.csvFile = open(self.csv_data_path, "r")
        self.csvReader = csv.reader(self.csvFile)
        self.strategy.setOrderAPI(self)
        self.logicName = "BackTester"
        self.plot_x, self.plot_y, self.color_map = [],[],[]
        
    def haltLogic(self):
        errorAndNotify("Halting the trader logic" + self.logicName)
        exit()

    def placeOrderAndSubscribe(self, orderInfo : OrderDescriptor, orderSubscription):
        self.curBackTestOrderID = self.curBackTestOrderID + 1
        orderInfo.orderID = self.curBackTestOrderID
        self.openOrders.append(orderInfo)
        self.inFlightOrders.append(orderInfo)
        return orderInfo.orderID

    def tick(self, date_time_str: str, open: Decimal, 
             high: Decimal, low: Decimal, close: Decimal, 
             volume: int, count: int, wap: Decimal):
        self.currentTick += 1
        print("Tick: " + str(self.currentTick))
        # TODO: Implement timeout for open orders
        curPrice = (open + high + low + close) / 4

        
        # execute in flight orders
        for order in self.inFlightOrders:
            # TODO: Implement fill price and fill quantity
            self.strategy.onSubmitted(order)
            self.strategy.onAccepted(order)
            self.inFlightOrders.remove(order)
        
        # execute open orders
        for order in self.openOrders:
            order_executed = False
            if order.orderInfo.action == "BUY":
                if order.orderInfo.lmtPrice >= curPrice:
                    order_executed = True
                    self.color_map.append("green")
            elif order.orderInfo.action == "SELL":
                if order.orderInfo.lmtPrice <= curPrice:
                    order_executed = True
                    self.color_map.append("red")

            if order_executed:
                # Update the order state
                order.orderInfo.status = "FILLED"
                order.currentFill = order.orderInfo.totalQuantity
                
                # order.OrderID = 
                order.currentRemaining = 0
                order.currentAverageFillPrice = curPrice
                order.avgFillPrice = curPrice
                order.lastFillPrice = curPrice
                order.orderInfo.filledQuantity = order.orderInfo.totalQuantity
                order.remainingQuantity = 0
                
                # Update the "Execution"
                execution = self.feeStructure.getExecution(order)
                execution.execId = self.currentExecutionID.__str__()
                self.strategy.onExecDetails(order, execution)

                # Update the Commission Report
                commission_report = self.feeStructure.getCommissionReport(order)
                commission_report.execId = self.currentExecutionID.__str__()
                self.strategy.onCommissionReport(order, commission_report)
                
                self.currentExecutionID += 1

                # Update backtester state
                self.executedOrders.append(order)
                self.openOrders.remove(order)
                
                # Call the backtested strategy 
                self.strategy.onFilled(order)
                    
                # Update the plot
                # TODO: Remove this
                self.plot_x.append(self.currentTick)
                self.plot_y.append(curPrice)
                


        # call update price
        self.strategy.onPriceUpdate(curPrice, BTC_CONTRACT)
    
    def run(self):
        with open(self.csv_data_path, "r") as csvFile:
            csvReader = csv.reader(csvFile)
            # skip header
            csvReader.__next__()
            for row in csvReader:
                self.tick(row[0], Decimal(row[1]), Decimal(row[2]), 
                          Decimal(row[3]), Decimal(row[4]), int(row[5]), 
                          int(row[6]), Decimal(row[7]))
                
        self.strategy.saveState()
        self.fig, self.ax = plt.subplots()
        plt.xlim(0,35000)
        plt.ylim(26000,29000)
        sc = self.ax.scatter(self.plot_x, self.plot_y, c= self.color_map)
        
        # annotate plot
        # for i, txt in enumerate(self.plot_y):
        #     self.ax.annotate(txt, (self.plot_x[i], self.plot_y[i]))
        
        plt.draw()
        plt.show()
        plt.waitforbuttonpress()
        
        


def main():
    strat = ConstantStepOffset()
    
    bt = BackTester(CSV_DATA_PATH, strat)
    bt.run()


if __name__ == "__main__":
    main()
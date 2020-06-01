from queue import Queue
from threading import Thread
import time
import grpc
from telegram_notifications.telegram_grpc.telegram_comms_pb2 import NotificationMessage
from telegram_notifications.telegram_grpc.telegram_comms_pb2_grpc import telegram_commsStub

## We always ensure that the TraderLogic "onPriceUpdate" is never calling a blocking method.
## To do that for messaging, we fork off a seperate thread. 
## That thread basically runs an event loop. The event loop executes the async method executions.
## The method that we expose (reccomend using) is not blocking as all it does is enqueues the "work" of sending message.

class TelegramNotificationsManager(Thread):
    # THE API call
    def sendNotification(self, message: str):
        self.my_q.put_nowait(message)

    def run(self):
        while True:
            print("waiting on queue")
            message_to_send = self.my_q.get()
            response = self.stub.sendNotification( NotificationMessage(message_str = message_to_send))
            print("telegram client received: " + str(response.success))
            self.my_q.task_done()

    def __init__(self):
        super().__init__(daemon=True)
        self.my_q = Queue()
        channel =  grpc.insecure_channel('localhost:50051')
        self.stub = telegram_commsStub(channel)
        self.start()
    
class TelegramNotificationsManagerStub(Thread):
    # THE API call
    def sendNotification(self, message: str):
        self.my_q.put_nowait(message)

    def run(self):
        while True:
            print("waiting on queue")
            message_to_send = self.my_q.get()
            print("message sent: " + message_to_send)
            self.my_q.task_done()

    def __init__(self):
        super().__init__(daemon=True)
        self.my_q = Queue()
        self.start()

# Small tester script
def main():
    manager = TelegramNotificationsManager()
    manager.sendNotification("Well hello there")
    time.sleep(2)
    manager.sendNotification("well good bye")

    manager.join()

if __name__ == "__main__":
    main()

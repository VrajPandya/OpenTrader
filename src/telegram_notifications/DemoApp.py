from TelegramNotifications import TelegramNotificationsManager
import time
import traceback
from threading import Thread
## This is a demo app that will send a notification every 2 seconds
class DemoApp(Thread):
    def __init__(self, manager) -> None:
        super().__init__()
        self.message_manager = manager
        self.start()

    def run(self):
            while True:
                try:
                    time.sleep(2)
                    self.message_manager.sendNotification("Hello there")
                except KeyboardInterrupt as e:
                     traceback.print_exception(e)


def trader_main():
    telegram_notification_manager = TelegramNotificationsManager()
    app = DemoApp(telegram_notification_manager)
    
    app.join()
    telegram_notification_manager.join()

    
if __name__ == "__main__":
    trader_main()

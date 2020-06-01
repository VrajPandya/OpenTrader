from concurrent import futures
from pathlib import Path
from telegram import Bot
import asyncio
import grpc
from telegram_grpc import telegram_comms_pb2
from telegram_grpc import telegram_comms_pb2_grpc
## We always ensure that the TraderLogic "onPriceUpdate" is never calling a blocking method.
## To do that for messaging, we fork off a seperate thread. 
## That thread basically runs an event loop. The event loop executes the async method executions.
## The method that we expose (reccomend using) is not blocking as all it does is enqueues the "work" of sending message.

class TelegramNotificationsManager(telegram_comms_pb2_grpc.telegram_commsServicer):
    def getConfDir(self):
        # Keep it verbose for dev :-)
        source_path = Path(__file__).resolve()
        telegram_source_dir = source_path.parent
        source_dir = telegram_source_dir.parent
        project_dir = source_dir.parent
        config_dir = project_dir.joinpath(self.BOT_KEY_DIR) 
        return config_dir

    def setTelegramToken(self):
        config_dir = self.getConfDir()
        token_file_path = config_dir.joinpath(self.BOT_KEY_FILE_NAME)
        with open(token_file_path, 'r') as token_file:
            self.TELEGRAM_TOKEN = token_file.read()

    def setTelegramChatIDForNotification(self):
        config_dir = self.getConfDir()
        chat_id_file_path = config_dir.joinpath(self.CHAT_ID_FILE_NAME)
        with open(chat_id_file_path, 'r') as chat_id_file:
            self.CHAT_ID = int(chat_id_file.read())

    def configureBot(self):
        self.setTelegramChatIDForNotification()
        self.setTelegramToken()

    # handle the API call.
    # we use the telegram bot library to call 
    def sendNotification(self, notification_message, context) -> telegram_comms_pb2.ServerReply:
        send_message_task = self.event_loop.create_task(coro=self.telegramBot.send_message(self.CHAT_ID, notification_message.message_str))
        self.event_loop.run_until_complete(send_message_task)
        fut = asyncio.ensure_future(send_message_task)
        
        asyncio.gather(fut)

        return telegram_comms_pb2.ServerReply(success= True)

    def __init__(self):
        self.CHAT_ID_FILE_NAME = "user_chat_id.conf"
        self.BOT_KEY_FILE_NAME = "bot_key.conf"
        self.BOT_KEY_DIR = "TraderGlobalConfig"
        self.TELEGRAM_TOKEN = "INVALID"
        self.CHAT_ID = 0
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        self.configureBot()
        self.telegramBot = Bot(self.TELEGRAM_TOKEN)

async def serve():
    port = '50051'
    

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    telegram_comms_pb2_grpc.add_telegram_commsServicer_to_server(TelegramNotificationsManager(), server)
    server.add_insecure_port('[::]:' + port)
    server.start()
    print("Server started, listening on " + port)
    server.wait_for_termination()


def main():
    bot = TelegramNotificationsManager()
    print(bot.TELEGRAM_TOKEN)
    print(bot.CHAT_ID)
    asyncio.run(serve())

if __name__ == "__main__":
    main()
import logging
from globalContext import GLOBAL_CONTEXT


def errorAndNotify(error_str):
    # global GLOBAL_CONTEXT
    GLOBAL_CONTEXT.telegramNotificationsManager.sendNotification(error_str)
    logging.error(error_str)

def infoAndNotify(info_str):
    # global GLOBAL_CONTEXT
    GLOBAL_CONTEXT.telegramNotificationsManager.sendNotification(info_str)
    logging.info(info_str)
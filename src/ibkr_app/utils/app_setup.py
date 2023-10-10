import logging
import os.path
import time

def SetupLogger(enable_consol_logs = False):
    pathToLogs = "extras/log"
    if not os.path.exists(pathToLogs):
        os.makedirs(pathToLogs)

    time.strftime("OpenTrader.%Y%m%d_%H%M%S.log")

    recfmt = '(%(threadName)s) %(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s'

    timefmt = '%y%m%d_%H:%M:%S'

    # logging.basicConfig( level=logging.DEBUG,
    #                    format=recfmt, datefmt=timefmt)
    logging.basicConfig(filename=time.strftime("extras/log/OpenTrader.%y%m%d_%H%M%S.log"),
                        filemode="w",
                        level=logging.INFO,
                        format=recfmt, datefmt=timefmt)
    if enable_consol_logs:
        logger = logging.getLogger()
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        logger.addHandler(console)
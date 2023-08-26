#!/bin/bash
# to run mongod as a seperate process
mongod --config TraderGlobalConfig/CryptoTrader_mongod_mac.conf --fork
# to stop mongod connect using mongosh and run `shutdown`

# Start the telegram server
sh scripts/start_telegram_server.sh




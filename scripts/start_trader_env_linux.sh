#!/bin/bash
#!/bin/bash

# Note: Try running the script from the project root directory
echo "if there are errors, try running the script from the project root directory"

# Start the mongo server
# to run mongod as a seperate process
mongod --config TraderGlobalConfig/CryptoTrader_mongod_linux.conf --fork

# Start the telegram server
sh scripts/start_telegram_server.sh





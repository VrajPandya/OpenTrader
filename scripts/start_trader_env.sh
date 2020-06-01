#!/bin/bash

brew services start mongodb-community@6.0

# to run mongod as a seperate process
# mongod --config /opt/homebrew/etc/mongod.conf --fork

# to stop mongod connect using mongosh and run `shutdown`



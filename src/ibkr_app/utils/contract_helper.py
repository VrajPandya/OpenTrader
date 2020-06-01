from ibapi.contract import Contract

def createContractDescriptor(symbol, secType, currency, exchange, primaryExchange):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = secType
    contract.currency = currency
    contract.exchange = exchange
    contract.primaryExchange = primaryExchange
    return contract 
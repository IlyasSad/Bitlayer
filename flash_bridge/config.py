from web3 import Web3

# RPC-адреса
bnb_RPC = 'https://bsc-pokt.nodies.app'
btl_RPC = 'https://rpc.bitlayer.org'

# Адрес USDT-контракта
usdt = Web3.to_checksum_address('0x55d398326f99059ff775485246999027b3197955')

# Сумма транзакции (в USDT)
amount = 10   #USDT

# Путь к ABI для USDT
usdt_abi_file = '../json_file/usdt_Abi.json'
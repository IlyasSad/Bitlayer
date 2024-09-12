from web3 import Web3

provider_url = 'https://rpc.bitlayer.org'

btc_address = Web3.to_checksum_address('0x0E4cF4Affdb72b39Ea91fA726D291781cBd020bF')
wbtc_address = Web3.to_checksum_address('0xfF204e2681A6fA0e2C3FaDe68a1B28fb90E4Fc5F')
swap_address = Web3.to_checksum_address('0xc6b0bbd9460217d7dc6d56305ed0cf74f3c4aa65')

swap_abi_file = '../json_file/Swap_ABI.json'
wbtc_abi_file = '../json_file/wBTC_Abi.json'
btc_abi_file = '../json_file/BTC_ABI.json'

count_btc_wBTC_makaron = 1
count_wBTC_btc_makaron = 1
count_BTC_wBTC_KOROVA = 1

amount = 0.00001
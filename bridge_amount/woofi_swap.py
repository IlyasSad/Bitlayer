from Crypto.SelfTest.Protocol.test_ecdh import private_key
from eth_account import Account, account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

with open('../json_file/woofi_abi.json', 'r') as file:
    abi = file.read()


with open('../json_file/woofi_token.json', 'r') as file:
    abi_token = file.read()

web3 = Web3(Web3.HTTPProvider('https://bsc.drpc.org'))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

contract_swap_woofi = Web3.to_checksum_address('0x4c4AF8DBc524681930a27b2F1Af5bcC8062E6fB7')
contract = web3.eth.contract(address=contract_swap_woofi, abi=abi)



fromToken = web3.to_checksum_address('0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c')
toToken = web3.to_checksum_address('0x55d398326f99059fF775485246999027B3197955')

contract_token = web3.eth.contract(address=fromToken, abi=abi_token)


key = '0x61809437c9c3fbf5a3835d9b411a2843a7fe48eabdf9b443fc3c06b0bc01067c'
address = Account.from_key(key).address

fromAmount = 70000000000000
minToAmount = 4403718000000000500

tx = contract_token.functions.approve(contract_swap_woofi,fromAmount).buildTransaction({
    'from': address,
    'nonce': web3.eth.get_transaction_count(address),
})
signed_tx = web3.eth.account.sign_transaction(tx, private_key=key)
tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"Транзакция отправлена: {tx_hash.hex()}")

receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
if receipt['status'] == 1:
    print(f"Транзакция успешна: {tx_hash.hex()}")

tx = contract.functions.swap(fromToken,toToken,fromAmount,minToAmount,address,address).build_transaction({
        'from': address,
        'nonce': web3.eth.get_transaction_count(address)
    })

signed_tx = web3.eth.account.sign_transaction(tx, private_key = key)
tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"Транзакция отправлена: {tx_hash.hex()}")

receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
if receipt['status'] == 1:
    print(f"Транзакция успешна: {tx_hash.hex()}")

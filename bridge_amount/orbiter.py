import asyncio
from web3.middleware import ExtraDataToPOAMiddleware
import requests
from eth_account import Account
from loguru import logger
from web3 import Web3

with open('../json_file/abi_orbiter.json', 'r') as file:
    abi = file.read()

async def main():
    key = 'e4a9ab2d2a5e925576f484cb54a13da000e6379f1cb6bd593080e54728f86d55'
    to = Web3.to_checksum_address('0xe01a40a0894970fc4c2b06f36f5EB94e73Ea502d')
    web3 = Web3(Web3.HTTPProvider('https://rpc.bitlayer.org'))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    value = web3.to_wei(0.00005, 'ether')

    contract_orbiter = Web3.to_checksum_address('0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172')
    contract = web3.eth.contract(address=contract_orbiter, abi=abi)
    address = Account.from_key(key).address
    data = f'c=9015&t={address}'
    print(data)
    data_bytes=data.encode('utf-8')
    print(data_bytes)
    data_hex = f'0x{data_bytes.hex()}'
    print(data_hex)
    tx = contract.functions.transfer(to,data_hex).build_transaction({
        'value': value,
        'from': address,
        'nonce': web3.eth.get_transaction_count(address)
    })

    signed_tx = web3.eth.account.sign_transaction(tx, key)
    tx_hash =  web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Транзакция отправлена: {tx_hash.hex()}")

    receipt =  web3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt['status'] == 1:
        print(f"Транзакция успешна: {tx_hash.hex()}")


if __name__ == "__main__":
    asyncio.run(main())
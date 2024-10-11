import asyncio

from eth_account import Account
from web3 import Web3

from flash_bridge.config import btl_RPC, bnb_RPC
from swap import config_swap
from swap.config_swap import wbtc_abi_file

with open('json_file/wBTC_Abi.json', 'r') as file:
    wbtc_abi = file.read()


async def check_balance_bitlayer(address, web3):
    balance = web3.eth.get_balance(address)
    return web3.from_wei(balance, 'ether')

async def check_balance_wbtc(wallet_address, web3_BTL):
    wbtc_contract = web3_BTL.eth.contract(address=config_swap.wbtc_address, abi=wbtc_abi)
    wallet_balance_wbtc =  wbtc_contract.functions.balanceOf(wallet_address).call()
    return web3_BTL.from_wei(wallet_balance_wbtc, 'ether')


async def main():
    with open('txt_files/keys.txt', 'r') as keys_file:
        keys = keys_file.readlines()
    with open('txt_files/proxy.txt', 'r') as file:
        proxies = [line.strip() for line in file]

    for index, private_key in enumerate(keys):
        private_key = private_key.strip()
        proxy = proxies[index % len(proxies)]
        account = Account.from_key(private_key)
        address = account.address
        web3 = Web3(Web3.HTTPProvider(bnb_RPC, request_kwargs={'proxies': {'http': proxy, 'https': proxy}}))
        balance = await check_balance_bitlayer(address, web3)

        print(f'{address} || {balance} bnb')

if __name__ == "__main__":
    asyncio.run(main())
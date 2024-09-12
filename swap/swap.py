import asyncio
import random
import time

from eth_account import Account
from loguru import logger
from web3 import Web3, AsyncWeb3, AsyncHTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
from custom_logger_swap import logging_setup
import config_swap

logging_setup()

# Загрузка ABI
with open(config_swap.swap_abi_file, 'r') as file:
    swap_abi = file.read()
with open(config_swap.wbtc_abi_file, 'r') as file:
    wbtc_abi = file.read()
with open(config_swap.btc_abi_file, 'r') as file:
    btc_abi = file.read()


async def contract_abi(web3):
    swap_contract = web3.eth.contract(address=config_swap.swap_address, abi=swap_abi)
    wbtc_contract = web3.eth.contract(address=config_swap.wbtc_address, abi=wbtc_abi)
    btc_contract = web3.eth.contract(address=config_swap.btc_address, abi=btc_abi)
    return swap_contract, wbtc_contract, btc_contract


# Загрузка прокси из файла
with open('../txt_files/proxy.txt', 'r') as f:
    proxies = [line.strip() for line in f]


async def process_wallet(private_key, base_amount, proxy, index, total_wallets):
    account = Account.from_key(private_key)
    address = account.address
    transaction_count = 0

    try:
        аsync_web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=config_swap.provider_url, request_kwargs={"proxy": proxy}))
        аsync_web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        swap_contract, wBTC_contract, btc_contract = await contract_abi(аsync_web3)

        wallet_balance_wbtc = await wBTC_contract.functions.balanceOf(address).call()
        wallet_balance_btc = await аsync_web3.eth.get_balance(address)
        logger.info(f'Баланс кошелька {address}: {аsync_web3.from_wei(wallet_balance_wbtc, "ether")} wBTC || {аsync_web3.from_wei(wallet_balance_btc, "ether")} BTC || Кошель {index}/{total_wallets} (Proxy: {proxy})')

        transactions = []
        for _ in range(config_swap.count_btc_wBTC_makaron):
            transactions.append((wBTC_contract.functions.deposit, 'deposit', base_amount))
        for _ in range(config_swap.count_wBTC_btc_makaron):
            transactions.append((wBTC_contract.functions.withdraw, 'withdraw', base_amount))
        for _ in range(config_swap.count_btc_wBTC_makaron):
            transactions.append((swap_contract.functions.swapBTCtoWBTC, 'swapBTCtoWBTC', base_amount))

        random.shuffle(transactions)

        for contract_function, transaction_type, amount in transactions:
            amount = random.uniform(amount * 0.90, amount * 1.35)  # Изменяем amount здесь
            amount = аsync_web3.to_wei(amount, 'ether')

            if transaction_type == 'deposit':
                # Депозит (BTC -> wBTC)
                if wallet_balance_btc >= amount:
                    name = 'BTC -> wBTC'
                    tx = await contract_function().build_transaction({
                        'from': address,
                        'value': amount,
                        'nonce':await аsync_web3.eth.get_transaction_count(address)
                    })
                    transaction_count += 1
                    await send_transaction(аsync_web3, tx, private_key, address, transaction_count, name)
                else:
                    logger.warning(f'Недостаточно BTC для депозита на кошельке {address}')
                    with open('ploxo_key_swap.txt', 'a') as f:
                        f.write(f"{private_key} | {address} - Недостаточно BTC для депозита\n")
            elif transaction_type == 'withdraw':
                # Вывод (wBTC -> BTC)
                if wallet_balance_wbtc >= amount:
                    name = 'wBTC -> BTC'
                    tx = await contract_function(amount).build_transaction({
                        'from': address,
                        'nonce': await аsync_web3.eth.get_transaction_count(address)
                    })
                    transaction_count += 1
                    await send_transaction(аsync_web3, tx, private_key, address, transaction_count, name)
                else:
                    logger.warning(f'Недостаточно wBTC для вывода на кошельке {address}')
                    with open('ploxo_key_swap.txt', 'a') as f:
                        f.write(f"{private_key} | {address} - Недостаточно wBTC для вывода\n")
            elif transaction_type == 'swapBTCtoWBTC':
                # Swap BTC to wBTC
                if wallet_balance_btc >= amount:
                    name = 'BTC -> wBTC Korova'
                    tx = await contract_function(config_swap.wbtc_address).build_transaction({
                        'from': address,
                        'value': amount,
                        'nonce': await аsync_web3.eth.get_transaction_count(address)
                    })
                    transaction_count += 1
                    await send_transaction(аsync_web3, tx, private_key, address, transaction_count, name)
                else:
                    logger.warning(f'Недостаточно BTC для swapBTCtoWBTC на кошельке {address}')
                    with open('ploxo_key_swap.txt', 'a') as f:
                        f.write(f"{private_key} | {address} - Недостаточно BTC для swapBTCtoWBTC\n")
            else:
                logger.error(f'Неизвестный тип транзакции: {transaction_type}')

    except Exception as e:
        logger.error(f'Ошибка при обработке кошелька {address}: {e} (Proxy: {proxy})')
        with open('ploxo_key_swap.txt', 'a') as f:
            f.write(f"{private_key} | {address} - {str(e)}\n")


async def send_transaction(web3_instance, tx, private_key, address, transaction_count, name):
    try:
        signed_tx = web3_instance.eth.account.sign_transaction(tx, private_key)
        tx_hash = await web3_instance.eth.send_raw_transaction(signed_tx.raw_transaction)
        await web3_instance.eth.wait_for_transaction_receipt(tx_hash)
        logger.success(f"Транзакция {name} выполнена: {web3_instance.to_hex(tx_hash)} для {address} - транзакция №{transaction_count}")
        sleep = random.randint(40, 62)
        logger.info(f'SLEEP {sleep} seconds..')
        time.sleep(sleep)
    except Exception as e:
        logger.error(f"Ошибка при отправке транзакции: {e}")
        with open('ploxo_key_swap.txt', 'a') as f:
            f.write(f"{private_key} | {address} - {str(e)}\n")



with open('../txt_files/keys.txt', 'r') as f:
    keys = [line.strip() for line in f]

async def main():
    base_amount = config_swap.amount
    total_wallets = len(keys)

    try:
        for i, private_key in enumerate(keys):
            proxy = proxies[i % len(proxies)]
            await process_wallet(private_key, base_amount, proxy, i, total_wallets)

    except Exception as e:
        logger.error(f'Ошибка: {e}')

if __name__ == "__main__":
    asyncio.run(main())
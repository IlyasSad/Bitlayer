import asyncio
import random
import time

from eth_account import Account
from loguru import logger
from web3 import Web3, AsyncWeb3, AsyncHTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
from custom_logger_swap import logging_setup
import config_swap
from asyncio import Semaphore

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

async def get_working_proxy(proxies):
    while True:
        rand_proxy = random.choice(proxies)

        web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=config_swap.provider_url, request_kwargs={"proxy": rand_proxy}))

        if await web3.is_connected():
            return rand_proxy


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
        logger.info(f'Баланс кошелька {address}: {аsync_web3.from_wei(wallet_balance_wbtc, "ether")} wBTC || {аsync_web3.from_wei(wallet_balance_btc, "ether")} BTC || Кошель {index + 1}/{total_wallets} (Proxy: {proxy})')

        transactions = []
        for _ in range(config_swap.count_btc_wBTC_makaron):
            transactions.append((wBTC_contract.functions.deposit, 'deposit', base_amount))
        for _ in range(config_swap.count_wBTC_btc_makaron):
            transactions.append((wBTC_contract.functions.withdraw, 'withdraw', base_amount))
        for _ in range(config_swap.count_BTC_wBTC_KOROVA):
            transactions.append((swap_contract.functions.swapBTCtoWBTC, 'swapBTCtoWBTC', base_amount))

        random.shuffle(transactions)

        min_btc_balance = аsync_web3.to_wei(0.000005, 'ether')  # Минимальный баланс BTC

        for contract_function, transaction_type, amount in transactions:
            amount = random.uniform(amount * 0.95, amount * 1.05)
            amount_wei = аsync_web3.to_wei(amount, 'ether')

            if transaction_type in ('deposit', 'swapBTCtoWBTC'):
                # Проверяем баланс BTC перед депозитом или свопом BTC -> wBTC
                if wallet_balance_btc < amount_wei or wallet_balance_btc < min_btc_balance:
                    logger.warning(f'Недостаточно BTC для {transaction_type} на кошельке {address}. '
                                   f'Пытаемся провести обратный свап...')
                    # Проводим обратный свап (wBTC -> BTC), если wBTC хватает
                    if wallet_balance_wbtc >= amount_wei:
                        amount_new = amount*1.18
                        amount_new_wei = аsync_web3.to_wei(amount_new, 'ether')
                        tx = await wBTC_contract.functions.withdraw(amount_new_wei).build_transaction({
                            'from': address,
                            'nonce': await аsync_web3.eth.get_transaction_count(address)
                        })

                        await execute_transaction(аsync_web3, tx,
                                                  private_key, address, transaction_count, 'wBTC -> BTC (обратный)', amount_wei)
                        wallet_balance_btc = await аsync_web3.eth.get_balance(address)  # Обновляем баланс BTC
                        logger.info(f'Новый баланс = {аsync_web3.from_wei(wallet_balance_btc, "ether")} BTC')
                        continue
                    else:
                        logger.warning(f'Недостаточно и wBTC для обратного свапа на кошельке {address}')
                        with open('ploxo_key_swap.txt', 'a') as f:
                            f.write(f"{private_key} | {address} - Недостаточно wBTC для обратного свапа\n")
                        continue  # Пропускаем транзакцию, если не хватает и wBTC

            if transaction_type == 'deposit':
                # Депозит (BTC -> wBTC)
                if wallet_balance_btc >= amount_wei:
                    name = 'BTC -> wBTC'
                    tx = await contract_function().build_transaction({
                        'from': address,
                        'value': amount_wei,
                        'nonce': await аsync_web3.eth.get_transaction_count(address)
                    })
                    await execute_transaction(аsync_web3, tx, private_key, address, transaction_count, name, amount_wei)
                else:
                    logger.warning(f'Недостаточно BTC для депозита на кошельке {address}')
                    with open('ploxo_key_swap.txt', 'a') as f:
                        f.write(f"{private_key} | {address} - Недостаточно BTC для депозита\n")
            elif transaction_type == 'withdraw':
                # Вывод (wBTC -> BTC)
                if wallet_balance_wbtc >= amount_wei:
                    name = 'wBTC -> BTC'
                    tx = await contract_function(amount_wei).build_transaction({
                        'from': address,
                        'nonce': await аsync_web3.eth.get_transaction_count(address)
                    })
                    await execute_transaction(аsync_web3, tx, private_key, address, transaction_count, name, amount_wei)
                else:
                    logger.warning(f'Недостаточно wBTC для вывода на кошельке {address}')
                    with open('ploxo_key_swap.txt', 'a') as f:
                        f.write(f"{private_key} | {address} - Недостаточно wBTC для вывода\n")
            elif transaction_type == 'swapBTCtoWBTC':
                # Swap BTC to wBTC
                if wallet_balance_btc >= amount_wei:
                    name = 'BTC -> wBTC Korova'
                    tx = await contract_function(config_swap.wbtc_address).build_transaction({
                        'from': address,
                        'value': amount_wei,
                        'nonce': await аsync_web3.eth.get_transaction_count(address)
                    })
                    await execute_transaction(аsync_web3, tx, private_key, address, transaction_count, name, amount_wei)
                else:
                    logger.warning(f'Недостаточно BTC для swapBTCtoWBTC на кошельке {address}')
                    with open('ploxo_key_swap.txt', 'a') as f:
                        f.write(f"{private_key} | {address} - Недостаточно BTC для swapBTCtoWBTC\n")
            else:
                logger.error(f'Неизвестный тип транзакции: {transaction_type}')

            # Обновляем балансы после каждой транзакции
            wallet_balance_wbtc = await wBTC_contract.functions.balanceOf(address).call()
            wallet_balance_btc = await аsync_web3.eth.get_balance(address)


    except Exception as e:
        logger.error(f'Ошибка при обработке кошелька {address}: {e} (Proxy: {proxy})')
        with open('ploxo_key_swap.txt', 'a') as f:
            f.write(f"{private_key} | {address} - {str(e)}\n")

async def execute_transaction(web3_instance, tx, private_key, address, transaction_count, name, amount=0):
    try:
        signed_tx = web3_instance.eth.account.sign_transaction(tx, private_key)
        tx_hash = await web3_instance.eth.send_raw_transaction(signed_tx.raw_transaction)
        await web3_instance.eth.wait_for_transaction_receipt(tx_hash)
        transaction_count += 1
        if amount > 0:
            logger.success(f"Транзакция {name} на сумму {web3_instance.from_wei(amount, 'ether')} выполнена: {web3_instance.to_hex(tx_hash)} для {address} - транзакция №{transaction_count}")
        else:
            logger.success(f"Транзакция {name} выполнена: {web3_instance.to_hex(tx_hash)} для {address} - транзакция №{transaction_count}")
        sleep = random.randint(20, 40)
        logger.info(f'SLEEP {sleep} seconds..')
        await asyncio.sleep(sleep)
    except Exception as e:
        logger.error(f"Ошибка при отправке транзакции: {e}")
        with open('ploxo_key_swap.txt', 'a') as f:
            f.write(f"{private_key} | {address} - {str(e)}\n")



with open('../txt_files/keys.txt', 'r') as f:
    privates = [line.strip() for line in f]

async def main():
    base_amount = config_swap.amount
    total_wallets = len(privates)

    semaphore = Semaphore(config_swap.potok)
    try:

        async def process_account_with_semaphore(private_key, base_amount, proxy, i, total_wallets):
            async with semaphore:
                return await process_wallet(private_key, base_amount, proxy, i, total_wallets)

        tasks = [process_account_with_semaphore(private, base_amount, await get_working_proxy(proxies), i, total_wallets)
             for i, private in enumerate(privates)]
        await asyncio.gather(*tasks)




    except Exception as e:
        logger.error(f'Ошибка: {e}')

if __name__ == "__main__":
    asyncio.run(main())
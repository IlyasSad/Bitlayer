import asyncio
import sys
import random
from time import sleep

from web3 import Web3, AsyncWeb3, AsyncHTTPProvider
from eth_account import Account
from loguru import logger
import json

# Константы
BITLAYER_RPC = "https://rpc.bitlayer.org"  # RPC URL сети Bitlayer
BTC_CONTRACT_ADDRESS = Web3.to_checksum_address('0x0E4cF4Affdb72b39Ea91fA726D291781cBd020bF')
AMOUNT_TO_SEND = 0.000002

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Загрузка ABI контракта BTC
with open('json_file//BTC_ABI.json', 'r') as abi_file:
    btc_abi = json.load(abi_file)


# Функция для получения баланса BTC
async def get_btc_balance(web3, address):
    btc_contract = web3.eth.contract(address=BTC_CONTRACT_ADDRESS, abi=btc_abi)
    balance = await btc_contract.functions.balanceOf(address).call()
    return balance / 10 ** 18  # Конвертируем из минимальных единиц в BTC


# Функция для отправки транзакции
async def send_btc_transaction(web3, from_address, private_key, to_address, amount):
    nonce = await web3.eth.get_transaction_count(Account.from_key(private_key).address)

    tx = {
        'from': from_address,
        "nonce": nonce,
        "to": to_address,
        "value": web3.to_wei(amount, 'ether'),
        "gas": 21000,
        "gasPrice": 50200000,
        "chainId": 200901
    }

    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Транзакция отправлена: {tx_hash.hex()}")

    receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt['status'] == 1:
        print(f"Транзакция успешна: {tx_hash.hex()}")
        return web3.to_hex(tx_hash)
    else:
        print(f"Ошибка транзакции: {tx_hash.hex()}")
        return 0



# Основная функция
async def main():
    # Загрузка списка кошельков для отправки из файла keys
    with open('txt_files/keys.txt', 'r') as file:
        keys = [line.strip() for line in file if line.strip()]

    with open('txt_files/proxy.txt', 'r') as file:
        proxies = [line.strip() for line in file if line.strip()]

    # Задаем исходный кошелек
    from_private_key = "e4a9ab2d2a5e925576f484cb54a13da000e6379f1cb6bd593080e54728f86d55"  # Приватный ключ исходного кошелька
    from_account = Account.from_key(from_private_key)
    from_address = from_account.address

    # Инициализация Web3


    # Отправка транзакций
    for index, to_private_key in enumerate(keys):
        to_account = Account.from_key(to_private_key)
        to_address = to_account.address

        proxy = random.choice(proxies) if proxies else None
        web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri='https://rpc.bitlayer.org', request_kwargs={"proxy": proxy}))

        # Проверка баланса исходного кошелька
        btc_balance = await get_btc_balance(web3, from_address)
        logger.info(f"Баланс исходного кошелька: {btc_balance} BTC")

        logger.info(f"Отправка {AMOUNT_TO_SEND} BTC с {from_address} на {to_address} ({index + 1}/{len(keys)})")

        try:
            tx_hash = await send_btc_transaction(web3, from_address, from_private_key, to_address, AMOUNT_TO_SEND)
            logger.info(f"Транзакция успешно отправлена. Хэш: {tx_hash}")
        except Exception as e:
            logger.error(f"Ошибка при отправке транзакции на {to_address}: {e}")
        await asyncio.sleep(5)


# Запуск основного процесса
if __name__ == "__main__":
    asyncio.run(main())

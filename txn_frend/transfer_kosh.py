import asyncio
import random
from asyncio import Semaphore
from decimal import Decimal

from eth_account import Account
from web3 import AsyncWeb3, AsyncHTTPProvider

# Конфигурация
RPC_URL = "https://rpc.bitlayer.org"
MAX_CONCURRENT_TRANSACTIONS = 10  # Максимальное количество одновременных транзакций

semaphore = Semaphore(MAX_CONCURRENT_TRANSACTIONS)


async def send_transaction(web3: AsyncWeb3, sender_key: str, recipient_address: str):
    """Отправляет весь баланс кошелька, за вычетом комиссии."""

    async with semaphore:
        sender_address = Account.from_key(sender_key).address
        balance = await web3.eth.get_balance(sender_address)

        # Оценка газа для транзакции
        gas_estimate = await web3.eth.estimate_gas({
            "from": sender_address,
            "to": recipient_address,
        })

        gas_price = await web3.eth.gas_price

        # Вычисляем максимальную сумму для отправки
        max_amount = balance - (gas_estimate * gas_price)

        if max_amount <= 0:
            print(f"Недостаточно средств на кошельке {sender_address} для оплаты комиссии")
            return

        nonce = await web3.eth.get_transaction_count(sender_address)

        tx = {
            "nonce": nonce,
            "to": recipient_address,
            "value": max_amount,  # Отправляем максимальную сумму
            "gas": gas_estimate,
            "gasPrice": gas_price,
            "chainId": 200901
        }

        signed_tx = web3.eth.account.sign_transaction(tx, sender_key)
        tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Транзакция отправлена: {tx_hash.hex()}")

        receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt['status'] == 1:
            print(f"Транзакция успешна: {tx_hash.hex()}")
            sleep = random.randint(1, 3)
            await asyncio.sleep(sleep)
        else:
            print(f"Ошибка транзакции: {tx_hash.hex()}")


async def get_working_proxy(proxies):
    """Проверяет прокси на работоспособность."""
    while True:
        rand_proxy = random.choice(proxies)

        web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=RPC_URL, request_kwargs={"proxy": rand_proxy}))

        if await web3.is_connected():
            return rand_proxy


async def main():
    """Основная функция скрипта."""
    with open('../txt_files/keys.txt', 'r') as f:
        lines = f.readlines()

    with open('../txt_files/proxy.txt', 'r') as f:
        proxies = [line.strip() for line in f]

    # Разделяем кошельки с деньгами и без денег
    wallets_with_funds = []
    wallets_without_funds = []
    current_list = wallets_with_funds

    for line in lines:
        line = line.strip()
        if not line:  # Пустая строка - разделитель
            current_list = wallets_without_funds
        else:
            current_list.append(line)

    total_wallets = len(wallets_with_funds)
    tasks = []

    for index, sender_key in enumerate(wallets_with_funds):
        proxy = await get_working_proxy(proxies)
        async_web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=RPC_URL, request_kwargs={"proxy": proxy}))
        sender_address = Account.from_key(sender_key).address
        print(f"Обработка кошелька: {sender_address}   ||   {index + 1}/{total_wallets}")

        if not wallets_without_funds:
            print("Все кошельки без средств получили переводы")
            break

        recipient_key = wallets_without_funds.pop(0)
        recipient_address = Account.from_key(recipient_key).address

        # Отправляем весь доступный баланс
        task = asyncio.create_task(send_transaction(async_web3, sender_key, recipient_address))
        tasks.append(task)

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
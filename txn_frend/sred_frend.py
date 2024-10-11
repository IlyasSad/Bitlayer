import asyncio
import random
from asyncio import Semaphore
from decimal import Decimal

from eth_account import Account
from web3 import AsyncWeb3, AsyncHTTPProvider

# Конфигурация
RPC_URL = "https://rpc.bitlayer.org"
MAX_CONCURRENT_TRANSACTIONS = 10
CHAIN_ID = 200901
TOLERANCE = Decimal("0.000002")

semaphore = Semaphore(MAX_CONCURRENT_TRANSACTIONS)
send_semaphore = Semaphore(1)

balances = {}  # Словарь для хранения балансов: {private_key: balance}


async def send_transaction(sender_key: str, recipient_address: str, amount_btc: float, proxies):
    """Отправляет транзакцию."""
    async with send_semaphore:
        proxy = await get_working_proxy(proxies)
        web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=RPC_URL, request_kwargs={"proxy": proxy}))
        nonce = await web3.eth.get_transaction_count(Account.from_key(sender_key).address)

        tx = {
            "nonce": nonce,
            "to": recipient_address,
            "value": web3.to_wei(amount_btc, 'ether'),
            "gas": 21000,
            "gasPrice": 50500000,
            "chainId": CHAIN_ID
        }

        signed_tx = web3.eth.account.sign_transaction(tx, sender_key)
        tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Транзакция отправлена: {tx_hash.hex()}")

        receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt['status'] == 1:
            print(f"Транзакция успешна: {tx_hash.hex()}")
            await asyncio.sleep(2)
        else:
            print(f"Ошибка транзакции: {tx_hash.hex()}")


async def get_working_proxy(proxies):
    while True:
        rand_proxy = random.choice(proxies)
        web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=RPC_URL, request_kwargs={"proxy": rand_proxy}))
        if await web3.is_connected():
            return rand_proxy


async def get_balance_btc(web3: AsyncWeb3, address: str) -> Decimal:
    """Получает баланс кошелька в BTC."""
    balance_wei = await web3.eth.get_balance(address)
    return Decimal(web3.from_wei(balance_wei, 'ether'))


async def get_total_balance(private_keys: list, proxies: list) -> Decimal:
    """Получает общий баланс по всем кошелькам."""

    total_balance = Decimal(0)
    i = 1
    async def get_balance_for_key(private_key: str):
        nonlocal i
        nonlocal total_balance  # Используем nonlocal для изменения внешней переменной
        proxy = await get_working_proxy(proxies)
        web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=RPC_URL, request_kwargs={"proxy": proxy}))
        address = Account.from_key(private_key).address
        balance = await get_balance_btc(web3, address)
        balances[private_key] = balance
        total_balance += balance
        print(f"{i}  Баланс кошелька {address}: {balance} BTC")
        i+=1

    tasks = [get_balance_for_key(key) for key in private_keys]
    await asyncio.gather(*tasks)

    return total_balance


async def main():
    with open('../txt_files/keys.txt', 'r') as f:
        private_keys = [line.strip() for line in f]

    with open('../txt_files/proxy.txt', 'r') as f:
        proxies = [line.strip() for line in f]


    total_balance = await get_total_balance(private_keys, proxies)
    average_balance = total_balance / len(private_keys)

    print(f"Общая сумма на кошельках: {total_balance} BTC")
    print(f"Средний баланс: {average_balance} BTC")

    tasks = []
    for private_key, sender_balance in balances.items():
        if sender_balance > average_balance + TOLERANCE:
            amount_to_send = sender_balance - average_balance
            for recipient_key, recipient_balance in balances.items():
                if recipient_key != private_key and recipient_balance < average_balance - TOLERANCE:
                    amount_to_receive = min(average_balance - recipient_balance, amount_to_send)
                    task = asyncio.create_task(
                        send_transaction(private_key, Account.from_key(recipient_key).address, amount_to_receive, proxies)
                    )
                    tasks.append(task)
                    # Обновляем балансы
                    balances[private_key] -= amount_to_receive
                    balances[recipient_key] += amount_to_receive

                    amount_to_send -= amount_to_receive
                    if amount_to_send == 0:
                        break

    await asyncio.gather(*tasks)

    print("Распределение завершено!")


if __name__ == "__main__":
    asyncio.run(main())
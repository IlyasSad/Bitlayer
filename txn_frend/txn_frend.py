import asyncio
import random
from asyncio import Semaphore

from eth_account import Account
from web3 import AsyncWeb3, AsyncHTTPProvider

# Конфигурация
RPC_URL = "https://rpc.bitlayer.org"
MAX_CONCURRENT_TRANSACTIONS = 5  # Максимальное количество одновременных транзакций

semaphore = Semaphore(MAX_CONCURRENT_TRANSACTIONS)

async def send_transaction(web3: AsyncWeb3, sender_key: str, recipient_address: str, amount_btc: float):
    """Отправляет транзакцию."""

    async with semaphore:  # Ожидаем освобождения слота в семафоре
        nonce = await web3.eth.get_transaction_count(Account.from_key(sender_key).address)

        tx = {
            "nonce": nonce,
            "to": recipient_address,
            "value": web3.to_wei(amount_btc, 'ether'),
            "gas": 21000,
            "gasPrice":  50200000,
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
    while True:
        rand_proxy = random.choice(proxies)

        web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=RPC_URL, request_kwargs={"proxy": rand_proxy}))

        if await web3.is_connected():
            return rand_proxy


async def main():
    with open('../txt_files/keys.txt', 'r') as f:
        private_keys = [line.strip() for line in f]

    with open('../txt_files/proxy.txt', 'r') as f:
        proxies = [line.strip() for line in f]

    total_wallets = len(private_keys)

    available_recipients = private_keys.copy()
    tasks = []

    for index, sender_key in enumerate(private_keys):
        proxy = await get_working_proxy(proxies)
        аsync_web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=RPC_URL, request_kwargs={"proxy": proxy}))
        sender_address = Account.from_key(sender_key).address
        print(f"Обработка кошелька: {sender_address}   ||   {index+1}/{total_wallets}")

        if len(available_recipients) <= 1:
            print(f"Недостаточно доступных получателей для {sender_address}")
            continue

        available_recipients.remove(sender_key)
        recipient_key = random.choice(available_recipients)
        recipient_address = Account.from_key(recipient_key).address

        amount_eth = random.uniform(0.000001, 0.00001)

        # Создаем задачу для отправки транзакции
        task = asyncio.create_task(send_transaction(аsync_web3, sender_key, recipient_address, amount_eth))
        tasks.append(task)

        available_recipients.append(sender_key)

    await asyncio.gather(*tasks) # Ожидание завершения всех задач

if __name__ == "__main__":
    asyncio.run(main())
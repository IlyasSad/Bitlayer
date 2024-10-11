import aiohttp
import asyncio
from web3 import AsyncWeb3, AsyncHTTPProvider
from eth_account import Account
from loguru import logger

from bridge_amount.config import amount


# Функция для отправки асинхронной транзакции
async def send_transaction(web3, tx_data, private_key):
    account = Account.from_key(private_key)
    nonce = await web3.eth.get_transaction_count(account.address)

    transaction = {
        'from': tx_data['from'],
        'to': tx_data['to'],
        'data': tx_data['data'],
        'value': 0,
        'nonce': nonce,
        'gas': 80000,
        'gasPrice': await web3.eth.gas_price,
        'chainId': 200901
    }

    signed_tx = web3.eth.account.sign_transaction(transaction, private_key = private_key)
    tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return web3.to_hex(tx_hash)

# Функция для выполнения транзакций на основе данных API
async def execute_bridge(web3, data, private_key):
    approve_body = data['data']['txs']['approve_body']
    transfer_body = data['data']['txs']['transfer_body']

    if approve_body:
        logger.info('Approving transaction...')
        approve_tx_hash = await send_transaction(web3, approve_body, private_key)
        logger.info(f"Approve транзакция отправлена: {approve_tx_hash}")

        # Ждем подтверждения
        receipt = await web3.eth.wait_for_transaction_receipt(approve_tx_hash)
        if receipt.status != 1:
            logger.error("Ошибка при выполнении approve транзакции.")
            return

        logger.info(f"Approve транзакция подтверждена: {approve_tx_hash}")
    else:
        logger.info("Approve транзакция не требуется")

    await asyncio.sleep(7)
    # 2. Транзакция transfer
    logger.info('Transferring transaction...')
    transfer_tx_hash = await send_transaction(web3, transfer_body, private_key)
    logger.info(f"Transfer транзакция отправлена: {transfer_tx_hash}")

    # Ждем подтверждения
    receipt = await web3.eth.wait_for_transaction_receipt(transfer_tx_hash)
    if receipt.status == 1:
        logger.info(f"Transfer успешен: {transfer_tx_hash}")
    else:
        logger.error(f"Transfer неуспешен: {transfer_tx_hash}")

    async with aiohttp.ClientSession() as session:
        while True:
            async with session.post(
                "https://owlto.finance/api/bridge_api/v1/get_receipt",
                json={"from_chain_hash": transfer_tx_hash}
            ) as response:
                data = await response.json()
                if data['status']['code'] == 0:
                    logger.success("Бабки успешно выведены!")
                    break
                else:
                    logger.info("Ожидание вывода средств...")
                    await asyncio.sleep(5)

# Функция для получения данных через API и выполнения транзакций
async def get_bridge_data_and_execute(private_key, proxy, a):
    account = Account.from_key(private_key)
    address = account.address

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://owlto.finance/api/bridge_api/v1/get_build_tx",
            json={
                "from_address": address,
                "from_chain_name": "BitlayerMainnet",
                "to_address": address,
                "to_chain_name": "BnbMainnet",
                "token_name": "USDT",
                "ui_value": str(amount-1.5-a)
            },
            proxy=proxy
        ) as response:
            data = await response.json()

    if data['status']['code'] == 0:
        logger.info("Данные для транзакций успешно получены")

        # Настройка Web3
        web3 = AsyncWeb3(AsyncHTTPProvider('https://rpc.bitlayer.org', request_kwargs={"proxy": proxy}))

        # Выполнение транзакций
        await execute_bridge(web3, data, private_key)
    else:
        logger.error(f"Ошибка получения данных: {data['status']['message']}")

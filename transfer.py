import asyncio

from eth_account import Account
from loguru import logger
from web3 import Web3

from flash_bridge import config

# Настройка логирования (необязательно, но полезно)
from flash_bridge.custom_logger import logging_setup
logging_setup()

# Установка соединения с блокчейном
web3 = Web3(Web3.HTTPProvider(config.bnb_RPC))

# Загрузка ABI для USDT
with open('json_file/usdt_Abi.json', 'r') as file:
    usdt_abi = file.read()

# Создание контракта USDT
usdt_contract = web3.eth.contract(address=config.usdt, abi=usdt_abi)

# Адрес получателя
recipient_address = "0x59a5Bc61BF9aAa931862Ed54EF80c7C56313dfD7"  # Замените на адрес получателя

async def send_usdt(private_key, amount):
    """
    Отправляет указанное количество USDT на адрес получателя.
    """
    try:
        account = Account.from_key(private_key)
        address = account.address


        # Оценка необходимого газа
        # estimated_gas = usdt_contract.functions.transfer(
        #     web3.to_checksum_address(recipient_address),
        #     int(amount * 10 ** 18)
        # ).estimate_gas({'from': address})

        # Газ
        # gas_price = web3.eth.gas_price
        # max_fee_per_gas = int(gas_price * 1.2)
        # max_priority_fee_per_gas = web3.to_wei('3', 'gwei')

        transaction = usdt_contract.functions.transfer(
            web3.to_checksum_address(recipient_address),
            int(amount * 10 ** 18)
        ).build_transaction({
            'nonce': web3.eth.get_transaction_count(address),
            'from': address,
            'gasPrice': web3.eth.gas_price + 20000,

        })

        # Подписание транзакции
        signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)

        # Отправка транзакции
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        logger.info(f'Транзакция отправлена, хэш: {web3.to_hex(tx_hash)}')

        # Ожидание подтверждения
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f'Транзакция подтверждена в блоке {receipt.blockNumber}')

    except Exception as e:
        logger.error(f'Ошибка при отправке транзакции: {e}')


async def main():
    private_key = "0x8f03d8462648ec145c606cb62136d232b4f164acbb751635800749dd86dae140"  # Замените на ваш приватный ключ
    amount = 0.0001  #  Количество USDT для отправки

    await send_usdt(private_key, amount)

if __name__ == "__main__":
    asyncio.run(main())
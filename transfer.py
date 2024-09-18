import asyncio

from eth_account import Account
from loguru import logger
from web3 import Web3

from flash_bridge import config

# Настройка логирования (необязательно, но полезно)
from flash_bridge.custom_logger import logging_setup
logging_setup()

# Установка соединения с блокчейном
web3 = Web3(Web3.HTTPProvider(config.btl_RPC))

# Загрузка ABI для USDT
with open('json_file/usdt_Abi.json', 'r') as file:
    usdt_abi = file.read()

# Создание контракта USDT
usdt_contract = web3.eth.contract(address=config.usdt, abi=usdt_abi)

# Адрес получателя
recipient_address = "0x02c806AA66655b5D2C1A7A1978128768d75e45E5"  # Замените на адрес получателя

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
        nonce =  web3.eth.get_transaction_count(address)

        tx = {
            "nonce": nonce,
            "to": recipient_address,
            "value": web3.to_wei(amount, 'ether'),
            "gas": 21000,
            "gasPrice": 50200000,
            "chainId": 200901
        }

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash =  web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Транзакция отправлена: {tx_hash.hex()}")

        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt['status'] == 1:
            print(f"Транзакция успешна: {tx_hash.hex()}")


    except Exception as e:
        logger.error(f'Ошибка при отправке транзакции: {e}')


async def main():
    private_key = '0x61809437c9c3fbf5a3835d9b411a2843a7fe48eabdf9b443fc3c06b0bc01067c'  # Замените на ваш приватный ключ
    amount = 0.00001  #

    await send_usdt(private_key, amount)

if __name__ == "__main__":
    asyncio.run(main())
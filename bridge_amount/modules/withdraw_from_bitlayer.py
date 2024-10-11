from eth_account import Account
from loguru import logger

from bridge_amount.config import ORBITER_ROUTER_ADDRESS, BTL_RPC
from utils.web3_helper import get_async_web3
from utils.logger import setup_logger


setup_logger()

async def withdraw_from_bitlayer(private_key, proxy):
    async_web3 = get_async_web3(BTL_RPC, proxy)
    account = Account.from_key(private_key)
    address = account.address
    ORBITER_ROUTER_ADDRESS1 = async_web3.to_checksum_address(ORBITER_ROUTER_ADDRESS)

    # Загрузка ABI контракта Orbiter Router
    with open('C:/Users/bkmzc/Bitleer/json_file/abi_orbiter.json', 'r') as file:
        orbiter_abi = file.read()

    contract = async_web3.eth.contract(address=ORBITER_ROUTER_ADDRESS1, abi=orbiter_abi)

    # Получение баланса BTC в минимальных единицах (сатоши)
    btc_balance = await async_web3.eth.get_balance(address)
    logger.info(f'баланс BTC в битлеере: {btc_balance}')

    # Конвертация баланса в BTC (предполагаем 18 десятичных знаков)
    decimals = 18
    btc_balance_decimal = btc_balance / 10 ** decimals


    # Вычитание 0.000033 BTC
    amount_to_send_decimal = btc_balance_decimal - 0.000005


    if amount_to_send_decimal <= 0:
        logger.error(f"Недостаточно BTC на кошельке {address} для выполнения транзакции.")
        return

    # Конвертация суммы обратно в минимальные единицы
    amount_to_send = int(amount_to_send_decimal * 10 ** decimals)

    # Подготовка данных для транзакции
    to_chain_c = '9015'
    data = f'c={to_chain_c}&t={address}'
    data_bytes = data.encode('utf-8')
    data_hex = f'0x{data_bytes.hex()}'

    # Получение текущего nonce
    nonce = await async_web3.eth.get_transaction_count(address)
    to = async_web3.to_checksum_address('0xe01a40a0894970fc4c2b06f36f5EB94e73Ea502d')

    tx = await contract.functions.transfer(to, data_hex).build_transaction({
        'value': amount_to_send,
        'from': address,
        'nonce': nonce
    })

    signed_tx = async_web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = await async_web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    logger.info(f"Транзакция отправлена: {tx_hash.hex()}")

    receipt = await async_web3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        logger.success(f"Транзакция успешна: {tx_hash.hex()}")
        logger.info('Бабки через Орбитер выведены!')
    else:
        logger.error(f"Транзакция неуспешна: {tx_hash.hex()}")

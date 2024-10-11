from eth_account import Account
from loguru import logger

from bridge_amount.config import BNB_RPC, USDT_ADDRESS, amount, amount_bridge
from utils.web3_helper import get_async_web3

async def send_to_exchange(private_key, exchange_address, proxy):
    web3 = get_async_web3(BNB_RPC, proxy)
    account = Account.from_key(private_key)
    address = account.address

    with open('C:/Users/bkmzc/Bitleer/json_file/usdt_Abi.json', 'r') as file:
        erc20_abi = file.read()

    USDT_ADDRESS1 = web3.to_checksum_address(USDT_ADDRESS)
    exchange_address1 = web3.to_checksum_address(exchange_address)
    usdt_contract = web3.eth.contract(address=USDT_ADDRESS1, abi=erc20_abi)

    # Получаем баланс USDT
    usdt_balance = await usdt_contract.functions.balanceOf(address).call()
    if usdt_balance == 0:
        logger.error(f"На кошельке {address} нет USDT для отправки.")
        return


    nonce = await web3.eth.get_transaction_count(address)
    tx = await usdt_contract.functions.transfer(
        exchange_address1,
        usdt_balance
    ).build_transaction({
        'from': address,
        'nonce': nonce,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    logger.info(f"Транзакция отправлена: {web3.to_hex(tx_hash)}")
    receipt = await web3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        logger.success(f"Отправка USDT успешна: {web3.to_hex(tx_hash)}")
        logger.info(f'Круг занял: {usdt_balance/10**18 - amount_bridge} USDT')
    else:
        logger.error(f"Отправка USDT неуспешна: {web3.to_hex(tx_hash)}")

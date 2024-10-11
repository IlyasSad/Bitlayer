import asyncio
from eth_account import Account
from loguru import logger

from bridge_amount.config import BNB_RPC, WOOFI_SWAP_ADDRESS, BTCB_ADDRESS, USDT_ADDRESS
from utils.web3_helper import get_async_web3

async def swap_btc_to_usdt(private_key, proxy):
    web3 = get_async_web3(BNB_RPC, proxy)
    account = Account.from_key(private_key)
    address = account.address

    with open('C:/Users/bkmzc/Bitleer/json_file/woofi_abi.json', 'r') as file:
        swap_abi = file.read()

    with open('C:/Users/bkmzc/Bitleer/json_file/woofi_token.json', 'r') as file:
        erc20_abi = file.read()

    swap_contract = web3.eth.contract(address=WOOFI_SWAP_ADDRESS, abi=swap_abi)
    btcb_contract = web3.eth.contract(address=BTCB_ADDRESS, abi=erc20_abi)

    # Получаем баланс BTCB
    btcb_balance = await btcb_contract.functions.balanceOf(address).call()
    if btcb_balance == 0:
        logger.error(f"На кошельке {address} нет BTCB для свапа.")
        return

    try:
        expected_usdt_amount = await swap_contract.functions.tryQuerySwap(
            BTCB_ADDRESS,
            USDT_ADDRESS,
            btcb_balance
        ).call()
    except Exception as e:
        logger.error(f"Ошибка при получении ожидаемого количества USDT: {e}")
        return

    # Устанавливаем допустимый процент проскальзывания (например, 1%)
    slippage_tolerance = 0.01
    min_to_amount = int(expected_usdt_amount * (1 - slippage_tolerance))
    logger.info(f'min_to_amount: {min_to_amount}')

    # 1. Апрув BTCB для свапа
    nonce = await web3.eth.get_transaction_count(address)
    tx_approve = await btcb_contract.functions.approve(
        WOOFI_SWAP_ADDRESS,
        btcb_balance
    ).build_transaction({
        'from': address,
        'nonce': nonce,
    })

    signed_tx_approve = web3.eth.account.sign_transaction(tx_approve, private_key)
    tx_hash_approve = await web3.eth.send_raw_transaction(signed_tx_approve.raw_transaction)
    logger.success(f"Транзакция апрува отправлена: {web3.to_hex(tx_hash_approve)}")
    await web3.eth.wait_for_transaction_receipt(tx_hash_approve)

    # 2. Свап BTCB на USDT
    nonce += 1
    tx_swap = await swap_contract.functions.swap(
        BTCB_ADDRESS,
        USDT_ADDRESS,
        btcb_balance,
        min_to_amount,
        address,
        address
    ).build_transaction({
        'from': address,
        'nonce': nonce,
    })

    signed_tx_swap = web3.eth.account.sign_transaction(tx_swap, private_key)
    tx_hash_swap = await web3.eth.send_raw_transaction(signed_tx_swap.raw_transaction)
    logger.info(f"Транзакция свапа отправлена: {web3.to_hex(tx_hash_swap)}")
    receipt = await web3.eth.wait_for_transaction_receipt(tx_hash_swap)
    if receipt.status == 1:
        logger.success(f"Свап успешен: {web3.to_hex(tx_hash_swap)}")
    else:
        logger.error(f"Свап неуспешен: {web3.to_hex(tx_hash_swap)}")

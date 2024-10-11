import asyncio
import random
import re
import sys

import aiohttp
from eth_account import Account
from loguru import logger
from web3 import AsyncHTTPProvider, AsyncWeb3
from fake_useragent import UserAgent
from web3.middleware import ExtraDataToPOAMiddleware

from bridge_amount.config import (
    BNB_RPC,
    BTL_RPC,
    USDT_ADDRESS, amount, amount_bridge,
)
from utils.web3_helper import get_async_web3
from utils.logger import setup_logger

# Initialize logging
setup_logger()

# Load USDT ABI
with open('C:/Users/bkmzc/Bitleer/json_file/usdt_Abi.json', 'r') as file:
    usdt_abi = file.read()
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def check_balance_usdt(address, usdt_contract):
    balance = await usdt_contract.functions.balanceOf(address).call()
    return balance / 10 ** 18

async def check_balance_bnb(address, web3):
    balance = await web3.eth.get_balance(address)
    return web3.from_wei(balance, 'ether')

async def check_balance_bitlayer(wallet_address, proxy):
    web3_btl = get_async_web3(BTL_RPC, proxy=proxy)
    balance = web3_btl.eth.get_balance(wallet_address)
    return balance

async def send_usdt(private_key, to_address, async_web3, amount = amount_bridge, retries=3):
    account = Account.from_key(private_key)
    address = account.address

    usdt_contract = async_web3.eth.contract(address=USDT_ADDRESS, abi=usdt_abi)
    usdt_balance = await check_balance_usdt(address, usdt_contract)
    bnb_balance = await check_balance_bnb(address, async_web3)

    logger.info(f'Баланс кошелька {address}: {usdt_balance} USDT, {bnb_balance} BNB')

    if usdt_balance < amount:
        return False, "Недостаточно USDT для отправки"

    attempts = 0
    gas_price = await async_web3.eth.gas_price

    while attempts < retries:
        try:
            nonce = await async_web3.eth.get_transaction_count(address)
            transaction = await usdt_contract.functions.transfer(
                async_web3.to_checksum_address(to_address),
                int(amount * 10 ** 18)
            ).build_transaction({
                'nonce': nonce,
                'from': address,
                'gasPrice': int(gas_price),
            })

            signed_txn = async_web3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = await async_web3.eth.send_raw_transaction(signed_txn.raw_transaction)

            await async_web3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info(f'Транзакция отправлена, хэш: {async_web3.to_hex(tx_hash)}')
            return True, async_web3.to_hex(tx_hash)

        except Exception as e:
            error_message = str(e)
            if "transaction underpriced" in error_message or "gas tip cap" in error_message:
                attempts += 1
                gas_price = int(gas_price * 1.2)
                logger.warning(f'Ошибка: {e}. Новая цена газа: {gas_price}. Попытка {attempts}/{retries}')
                await asyncio.sleep(2 ** attempts)
                usdt_balance = await check_balance_usdt(address, usdt_contract)
                if usdt_balance < amount:
                    return False, "Недостаточно USDT после повторной проверки"
            else:
                return False, str(e)

    return False, f"Не удалось отправить транзакцию после {retries} попыток."

async def make_get_request(session, url, headers=None, proxy=None):
    async with session.get(url, headers=headers, proxy=proxy) as response:
        response.raise_for_status()
        return await response.json()

async def make_post_request(session, url, data=None, headers=None, proxy=None):
    async with session.post(url, headers=headers, data=data, proxy=proxy) as response:
        response.raise_for_status()
        return response

async def process_wallet(private_key, proxy):
    account = Account.from_key(private_key)
    wallet_address = account.address
    logger.info(f'Обработка кошелька {wallet_address} с прокси {proxy}')



    async with aiohttp.ClientSession() as session:
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Origin': 'https://www.bitlayer.org',
            'Referer': 'https://www.bitlayer.org/flash-bridge',
            'User-Agent': UserAgent().random,
        }

        # Step 1: Get request ID
        response = await make_get_request(
            session,
            'https://www.bitlayer.org/flash-bridge?_data=routes%2F%28%24lang%29._app%2B%2Fflash-bridge%2B%2F_index',
            headers=headers,
            proxy=proxy
        )
        request_id = response.get('requestId')
        if not request_id:
            logger.error("Не удалось получить request ID")
            return False

        # Step 2: Create order
        body = {
            'amount': amount_bridge,
            'from_coin': 'USDT',
            'to_coin': 'USDT',
            'language': 'en',
            'source': '',
            'address': wallet_address,
            'request_id': request_id
        }

        response = await make_post_request(
            session,
            'https://www.bitlayer.org/flash-bridge/order?_data=routes%2F%28%24lang%29._app%2B%2Fflash-bridge%2B%2Forder',
            data=body,
            headers=headers,
            proxy=proxy
        )
        redirect_url = response.headers.get('X-Remix-Redirect')

        match = re.search(r'/orders/([a-f0-9\-]+)', redirect_url)
        if not match:
            logger.error("Order ID не найден в redirect URL")
            return False

        order_id = match.group(1)
        logger.info(f"Order ID: {order_id} для {wallet_address}")

        # Step 3: Get payment details
        response = await make_get_request(
            session,
            f'https://www.bitlayer.org/flash-bridge/orders/{order_id}?_data=routes%2F%28%24lang%29._app%2B%2Fflash-bridge%2B%2Forders.%24id',
            headers=headers,
            proxy=proxy
        )
        payments = response.get('payments', [])
        to_address = None
        for payment in payments:
            if payment.get('asset') == 'USDT_BNB':
                to_address = payment.get('address')
                break

        if not to_address:
            logger.error("Адрес для отправки USDT не найден")
            return False

        # Step 4: Send USDT
        web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=BNB_RPC, request_kwargs={"proxy": proxy}))
        web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        success, tx_result = await send_usdt(private_key, to_address, web3)
        if success:
            logger.success(f"USDT отправлены успешно, tx_hash: {tx_result}")
            # Optionally, wait for confirmation on Bitlayer
            return True
        else:
            logger.error(f"Ошибка при отправке USDT: {tx_result}")
            return False

async def get_working_proxy(proxies):
    while True:
        rand_proxy = random.choice(proxies)
        try:
            web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=BNB_RPC, request_kwargs={"proxy": rand_proxy}))
            if await web3.is_connected():
                return rand_proxy
        except Exception:
            continue

async def bridge_to_bitlayer(private_key, proxy):
    success = await process_wallet(private_key, proxy)
    return success



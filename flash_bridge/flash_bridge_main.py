import asyncio
import random
import re
import sys

import aiohttp
from eth_account import Account
from loguru import logger
from web3 import Web3, AsyncWeb3, AsyncHTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware

import config
from custom_logger import logging_setup
from fake_useragent import UserAgent

logging_setup()

with open(config.usdt_abi_file, 'r') as file:
    usdt_abi = file.read()

success_count = 0
failure_count = 0

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def check_balance_usdt(address, usdt_contract):
    balance = await usdt_contract.functions.balanceOf(address).call()
    return balance / 10 ** 18


async def check_balance_bnb(address, web3):
    balance = await web3.eth.get_balance(address)
    return web3.from_wei(balance, 'ether')


async def check_balance_bitlayer(wallet_address, proxy):
    web3_BTL = Web3(Web3.HTTPProvider(config.btl_RPC, request_kwargs={'proxies': {'http': proxy, 'https': proxy}}))
    balance = web3_BTL.eth.get_balance(wallet_address)
    return balance


async def bridge(private_key, to, AsyncWeb3: AsyncWeb3, retries=3):
    account = Account.from_key(private_key)
    address = account.address

    usdt_contract = AsyncWeb3.eth.contract(address=config.usdt, abi=usdt_abi)
    usdt_balance = await check_balance_usdt(address, usdt_contract)
    bnb_balance = await check_balance_bnb(address, AsyncWeb3)

    logger.info(f'Баланс кошелька {address}: {usdt_balance} USDT, {bnb_balance} BNB')

    if usdt_balance < config.amount:
        return False, "Недостаточно USDT для отправки"

    attempts = 0
    gas_price = await AsyncWeb3.eth.gas_price

    while attempts < retries:
        try:
            transaction =await usdt_contract.functions.transfer(
                AsyncWeb3.to_checksum_address(to),
                int(config.amount * 10 ** 18)
            ).build_transaction({
                'nonce': await AsyncWeb3.eth.get_transaction_count(address),
                'from': address,
                'gasPrice': int(gas_price),
            })

            signed_txn = AsyncWeb3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = await AsyncWeb3.eth.send_raw_transaction(signed_txn.raw_transaction)

            await AsyncWeb3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info(f'Транзакция отправлена, хэш: {AsyncWeb3.to_hex(tx_hash)}')
            return True, AsyncWeb3.to_hex(tx_hash)

        except Exception as e:
            error_message = str(e)
            if "transaction underpriced" in error_message or "gas tip cap" in error_message:
                attempts += 1
                gas_price = int(gas_price * 1.2)
                logger.warning(f'Ошибка: {e}. Новая цена газа: {gas_price}. Попытка {attempts}/{retries}')
                await asyncio.sleep(2 ** attempts)
                usdt_balance = await check_balance_usdt(address, usdt_contract)
                if usdt_balance < config.amount: return True, f"Прошел по приколу"
            else:
                return False, str(e)


    return False, f"Не удалось отправить транзакцию после {retries} попыток."


async def make_get_request(session, url, headers=None, proxy=None):
    async with session.get(url, headers=headers, proxy=proxy) as response:
        response.raise_for_status()
        return await response.json()


async def make_post_request(session, url, body=None, headers=None, proxy=None):
    async with session.post(url, headers=headers, data=body, proxy=proxy) as response:
        response.raise_for_status()
        return response


async def make_get_params(session, url, params, headers=None, proxy=None):
    async with session.get(url, params=params, headers=headers, proxy=proxy) as response:
        response.raise_for_status()
        return await response.json()


async def process_wallet(private_key, session, headers, request_id, proxy, web3):
    global success_count, failure_count

    account = Account.from_key(private_key)
    wallet_address = account.address
    logger.info(f'Обработка кошелька {wallet_address} с прокси {proxy}')

    body = {
        'amount': config.amount,
        'from_coin': 'USDT',
        'to_coin': 'BTC',
        'language': 'en',
        'source': '',
        'address': wallet_address,
        'request_id': request_id
    }

    try:
        response = await make_post_request(
            session,
            'https://www.bitlayer.org/flash-bridge/order?_data=routes%2F%28%24lang%29._app%2B%2Fflash-bridge%2B%2Forder',
            body,
            headers,
            proxy=proxy
        )
        redirect_url = response.headers.get('X-Remix-Redirect')

        match = re.search(r'/orders/([a-f0-9\-]+)', redirect_url)
        if match:
            order_id = match.group(1)
            logger.info(f"Order ID: {order_id} для {wallet_address}")

            response = await make_get_request(
                session,
                f'https://www.bitlayer.org/flash-bridge/orders/{order_id}?_data=routes%2F%28%24lang%29._app%2B%2Fflash-bridge%2B%2Forders.%24id',
                headers,
                proxy=proxy
            )
            for payment in response['payments']:
                if payment['asset'] == 'USDT_BNB':
                    to = payment['address']
                    success, tx_result = await bridge(private_key, to, web3)
                    if success:
                        logger.info(f'Ждем ответа от https://www.bitlayer.org/')
                        for _ in range(6):
                            bitlayer_balance =await check_balance_bitlayer(wallet_address, proxy)
                            if bitlayer_balance > 0:
                                with open('../txt_files/Nice_key.txt', 'a') as file:
                                    file.write(f"{wallet_address} || {private_key} || {tx_result}\n")
                                success_count += 1
                                logger.success(f'{wallet_address} получил Bitcoin')
                                break
                            await asyncio.sleep(15)
                        else:
                            with open('../txt_files/Ploxo_key.txt', 'a') as file:
                                file.write(
                                    f"{wallet_address} || {private_key} || Денежные средства не возвращены, {tx_result}\n")
                            failure_count += 1
                            logger.error(f'Ошибка для {wallet_address}: Денежные средства не возвращены')
                    else:
                        with open('../txt_files/Ploxo_key.txt', 'a') as file:
                            file.write(f"{wallet_address} || {private_key} || {tx_result}\n")
                        failure_count += 1
                        logger.error(f'Ошибка для {wallet_address}: {tx_result}')
                    break
        else:
            logger.error("Order ID не найден в redirect URL")
            with open('../txt_files/Ploxo_key.txt', 'a') as file:
                file.write(f"{wallet_address} || {private_key} || Ошибка: Order ID не найден\n")
            failure_count += 1

    except Exception as e:
        logger.error(f'Ошибка при обработке кошелька {wallet_address}: {e}')
        with open('../txt_files/Ploxo_key.txt', 'a') as file:
            file.write(f"{wallet_address} || {private_key} || Ошибка: {str(e)}\n")
        failure_count += 1


async def get_working_proxy(proxies):
    while True:
        rand_proxy = random.choice(proxies)

        web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=config.bnb_RPC, request_kwargs={"proxy": rand_proxy}))

        if await web3.is_connected():
            return rand_proxy


async def main():
    with open('../txt_files/proxy.txt', 'r') as file:
        proxies = [line.strip() for line in file]

    with open('../txt_files/keys.txt', 'r') as keys_file:
        keys = keys_file.readlines()

    total_wallets = len(keys)
    logger.info(f"Всего кошельков для обработки: {total_wallets}")

    for index, private_key in enumerate(keys):
        async with aiohttp.ClientSession() as session:
            headers = {
                'accept': '*/*',
                'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'no-cache',
                'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'dnt': '1',
                'origin': 'https://www.bitlayer.org',
                'pragma': 'no-cache',
                'priority': 'u=1, i',
                'referer': 'https://www.bitlayer.org/flash-bridge',
                'sec-ch-ua-mobile': '?0',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': UserAgent(os='windows').random
            }

            private_key = private_key.strip()
            proxy = await get_working_proxy(proxies)

            web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=config.bnb_RPC, request_kwargs={"proxy": proxy}))
            web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            response = await make_get_request(
                session,
                'https://www.bitlayer.org/flash-bridge?_data=routes%2F%28%24lang%29._app%2B%2Fflash-bridge%2B%2F_index',
                proxy=proxy
            )
            request_id = response['requestId']

            logger.info(f'Обработка кошелька {index + 1} из {total_wallets}')

            await process_wallet(private_key, session, headers, request_id, proxy, web3)
            sleep = random.randint(40, 60)

            logger.info(f'Sleep {sleep} seconds..')
            await asyncio.sleep(sleep)

    logger.info(f"Количество успешных кошельков: {success_count}")
    logger.info(f"Количество неуспешных кошельков: {failure_count}")


if __name__ == "__main__":
    asyncio.run(main())

    # logger.info(f'Ждем ответа от https://www.bitlayer.org/')
    # time.sleep(80)
    # params = {'address': wallet_address}
    # response = await make_get_params(session, 'https://www.bitlayer.org/flash-bridge/orders', params, headers, proxy)
    # bitlayer_success = False
    # for transaction in response:
    #     if transaction['status'] == 2:
    #         bitlayer_success = True
    #         break

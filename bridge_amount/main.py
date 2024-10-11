import asyncio
import json
import logging
import random
from loguru import logger
from web3 import Web3, AsyncWeb3, AsyncHTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware

from bridge_amount.modules import send_to_wallet
from bridge_amount.modules.chek_wallet import check_usdt_balance
from bridge_amount.modules.owlto_w_b import get_bridge_data_and_execute
from bridge_amount.modules.send_to_wallet import withdraw_from_bitget
from modules.bridge_to_bitlayer import bridge_to_bitlayer
from modules.withdraw_from_bitlayer import withdraw_from_bitlayer
from modules.swap_btc_to_usdt import swap_btc_to_usdt
from modules.send_to_exchange import send_to_exchange
from utils.logger import setup_logger
from bridge_amount.config import SLEEP_TIME, BNB_RPC, USDT_ADDRESS, amount, amount_bridge
from eth_account import Account

from utils.web3_helper import get_balance

logging.getLogger('asyncio').setLevel(logging.CRITICAL)
async def main():
    setup_logger()

    with open('deposit_wallet.txt', 'r') as file:
        deposit_wallet = [line.strip() for line in file if line.strip()]

    with open('../txt_files/keys.txt', 'r') as file:
        private_keys = [line.strip() for line in file if line.strip()]

    with open('..//json_file//usdt_Abi.json', 'r') as file:
        usdt_abi = json.load(file)

    with open('../txt_files/proxy.txt', 'r') as file:
        proxies = [line.strip() for line in file if line.strip()]

    total_wallets = len(private_keys)
    logger.info(f"Всего кошельков для обработки: {total_wallets}")

    total_deposit_wallets = len(deposit_wallet)
    logger.info(f"Всего депозитных кошельков: {total_deposit_wallets}")


    for index, private_key in enumerate(private_keys):
        account = Account.from_key(private_key)
        address = account.address
        logger.info(f"Начало обработки кошелька {index + 1}/{total_wallets} || {address}")
        proxy = random.choice(proxies) if proxies else None

        web3 = AsyncWeb3(AsyncHTTPProvider(endpoint_uri=BNB_RPC, request_kwargs={"proxy": proxy}))
        usdt_contract = web3.eth.contract(address=USDT_ADDRESS, abi=usdt_abi)

        deposit_index = index % total_deposit_wallets
        exchange_address = deposit_wallet[deposit_index]
        logger.info(f"Используется депозитный кошелек {exchange_address} для отправки USDT обратно.")

        if await check_usdt_balance():
            logger.info(f'Жду перевода на {address}')
            withdraw_from_bitget(address)
            while True:
                balance = await usdt_contract.functions.balanceOf(address).call()
                balance_wei = Web3.from_wei(balance, "ether")
                logger.info(f'balance: {balance_wei}')
                if balance_wei > amount_bridge-1:
                    break
                await asyncio.sleep(random.randint(*SLEEP_TIME))
        else:
            logger.error('Ошибка BITGET')
            return


        try:
            await bridge_to_bitlayer(private_key, proxy)

            await asyncio.sleep(random.randint(*SLEEP_TIME))

            await get_bridge_data_and_execute(private_key, proxy, 0)

            await asyncio.sleep(random.randint(*SLEEP_TIME))

            await get_bridge_data_and_execute(private_key, proxy, 1)


            # Свап BTCB в USDT
            # await swap_btc_to_usdt(private_key, proxy)

            await asyncio.sleep(random.randint(*SLEEP_TIME))

            await send_to_exchange(private_key, exchange_address, proxy)

            logger.info('Sleep..')
            await asyncio.sleep(random.randint(400,600))

        except Exception as e:
            logger.error(f"Произошла ошибка при обработке кошелька {address}: {e}")

    logger.info("Все кошельки обработаны.")

if __name__ == '__main__':
    asyncio.run(main())

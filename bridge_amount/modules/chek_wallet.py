import asyncio

import ccxt.async_support as ccxt
from win32comext.adsi.demos.scp import logger


async def check_usdt_balance():
    exchange = ccxt.bitget({
        'apiKey': 'bg_c580e9a471678920e86ae6e7829c37fc',
        'secret': 'd46f731b07bb8cda61f4d2d3607fb60546dca2cc8d308a65076235bac11d3a9d',
        'password': 'qweasdzxc',  # Include if required
    })
    try:
        while True:
            balance = await exchange.fetch_balance()
            usdt_balance = balance['total'].get('USDT', 0)
            logger.info(f"Ваш баланс USDT: {usdt_balance}")

            if usdt_balance >= 999:
                await exchange.close()  # Закрываем соединение
                return True
            else:
                await asyncio.sleep(10)  # Ждем перед следующей проверкой
    except ccxt.AuthenticationError as e:
        print(f"Ошибка аутентификации: {e}")
        await exchange.close()
        return False
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        await exchange.close()
        return False





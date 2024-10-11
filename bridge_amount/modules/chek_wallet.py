import asyncio

import ccxt.async_support as ccxt
from win32comext.adsi.demos.scp import logger


async def check_usdt_balance():
    exchange = ccxt.bitget({
        'apiKey': '',
        'secret': '',
        'password': '',  # Include if required
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





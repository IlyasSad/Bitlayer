import ccxt
from loguru import logger

from bridge_amount.config import amount_bridge


def withdraw_from_bitget(address=None,amount = amount_bridge, network='BEP20'):

    exchange = ccxt.bitget({
        'apiKey': 'bg_c580e9a471678920e86ae6e7829c37fc',
        'secret': 'd46f731b07bb8cda61f4d2d3607fb60546dca2cc8d308a65076235bac11d3a9d',
        'password': 'qweasdzxc',
        'enableRateLimit': True,
    })

    # Проверяем, поддерживается ли вывод через API
    if exchange.has.get('withdraw'):
        currency = 'USDT'

        try:
            # Параметры для вывода
            params = {
                'chain': network,
            }

            # Выполнение вывода средств
            withdrawal = exchange.withdraw(
                code=currency,
                amount=amount,
                address=address,
                params=params
            )

            logger.success("Вывод средств выполнен успешно:")
            return withdrawal

        except ccxt.InsufficientFunds as e:
            print(f"Недостаточно средств: {e}")
        except ccxt.ExchangeError as e:
            print(f"Ошибка биржи: {e}")
        except Exception as e:
            print(f"Произошла ошибка: {e}")
    else:
        print("Вывод средств через API не поддерживается для Bitget в CCXT.")

    return None

import asyncio
import json
import random
import aiohttp

from eth_account import Account
from eth_account.messages import encode_defunct
from fake_useragent import UserAgent
from web3 import AsyncWeb3, AsyncHTTPProvider
from custom_logger_task import logging_setup
from loguru import logger
from config_task import RPC_URL, TASK_IDS

logging_setup()

# Максимальное количество одновременных запросов
MAX_CONCURRENT_REQUESTS = 10  # Настройте это значение по своему усмотрению

semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


async def request_post(session, url, body=None, headers=None, proxy=None):
    async with semaphore:
        try:
            async with await session.post(
                url, headers=headers, data=body, proxy=proxy
            ) as response:
                if response.status != 200:
                    logger.error(
                        f"Ошибка запроса: {response.status} для URL: {url}"
                    )
                    return None
                return response
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса к {url}: {e}")
            return None


async def signature_key(text: str, private_key: str, web3: AsyncWeb3) -> str:
    signature = web3.eth.account.sign_message(
        encode_defunct(AsyncWeb3.to_bytes(text=text)), f"0x{private_key}"
    )
    return f"0x{signature.signature.hex()}"


async def claim_task(
    session: aiohttp.ClientSession,
    headers: dict,
    task_id: int,
    task_type: int,
    proxy: str,
    address: str,
) -> aiohttp.ClientResponse:
    json_data = {"taskId": task_id}

    response = await request_post(
        session,
        "https://www.bitlayer.org/me/task/start",
        json.dumps(json_data),
        headers,
        proxy,
    )
    if response and response.status == 200:
        logger.info(f"Start id = {task_id} in {address}")

    json_data_claim = {
        "taskId": task_id,
        "taskType": task_type,
    }

    response = await request_post(
        session,
        "https://www.bitlayer.org/me/task/verify",
        json.dumps(json_data),
        headers,
        proxy,
    )
    if response is None:
        return None

    response = await request_post(
        session,
        "https://www.bitlayer.org/me/task/claim",
        json.dumps(json_data_claim),
        headers,
        proxy=proxy,
    )
    return response


async def get_working_proxy(proxies):
    for _ in range(len(proxies) * 3):  # Попробуем каждый прокси несколько раз
        rand_proxy = random.choice(proxies)
        provider = AsyncHTTPProvider(
            endpoint_uri=RPC_URL, request_kwargs={"proxy": rand_proxy}
        )
        web3 = AsyncWeb3(provider)
        try:
            if await web3.is_connected():
                return rand_proxy
            else:
                logger.warning(f"Прокси {rand_proxy} не работает.")
        except Exception as e:
            logger.error(f"Ошибка при проверке прокси {rand_proxy}: {e}")
    logger.error("Не удалось найти рабочий прокси.")
    return None


async def process_account(
    session: aiohttp.ClientSession, address: str, private_key: str, proxy: str
):
    if not proxy:
        logger.error(f"Для кошелька {address} не удалось получить рабочий прокси.")
        return

    headers = {
        "accept": "*/*",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "no-cache",
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
        "dnt": "1",
        "origin": "https://www.bitlayer.org",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://www.bitlayer.org/me",
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": UserAgent(os="windows").random,
    }

    async_web3 = AsyncWeb3(
        AsyncHTTPProvider(endpoint_uri=RPC_URL, request_kwargs={"proxy": proxy})
    )
    signature = await signature_key("BITLAYER", private_key, async_web3)

    login_data = {"address": address, "signature": signature}
    login_response = await request_post(
        session,
        "https://www.bitlayer.org/me/login",
        json.dumps(login_data),
        headers,
        proxy,
    )
    if login_response is None:
        logger.error(f"Ошибка авторизации для кошелька {address}")
        return

    session_cookie = login_response.headers.get("Set-Cookie")
    if not session_cookie:
        logger.error(f"Не удалось получить куки для кошелька {address}")
        return
    headers["Cookie"] = session_cookie

    for task in TASK_IDS:
        response = await claim_task(
            session, headers, task["id"], task["type"], proxy, address
        )
        if response and response.status == 200:
            logger.success(
                f"Аккаунт {address}: Задача {task['id']} успешно заклеймена!"
            )
            sleep = random.randint(5, 10)
            logger.info(f"Sleep {sleep} seconds..")
            await asyncio.sleep(sleep)
        else:
            logger.error(
                f"Аккаунт {address}: Ошибка при клейме задачи {task['id']}:"
                f" {response.status if response else 'Нет ответа'}"
            )


async def main():
    with open("../txt_files/keys.txt", "r") as f:
        keys = [line.strip() for line in f]
    with open("../txt_files/proxy.txt", "r") as f:
        proxies = [line.strip() for line in f]

    total_wallets = len(keys)
    tasks = []

    async with aiohttp.ClientSession() as session:
        for index, private_key in enumerate(keys):
            logger.info(f"Обработка кошелька {index + 1} из {total_wallets}")
            proxy = await get_working_proxy(proxies)
            tasks.append(
                asyncio.create_task(
                    process_account(
                        session,
                        Account.from_key(private_key).address,
                        private_key,
                        proxy,
                    )
                )
            )

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
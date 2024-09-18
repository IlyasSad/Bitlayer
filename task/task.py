import asyncio
import json
import time
from enum import Enum

import aiohttp
from aiohttp import ClientSession
from eth_account.messages import encode_defunct
from web3 import Web3
from custom_logger_task import logging_setup
from loguru import logger


logging_setup()

PRIVATE_KEY = ''
PUBLIC_KEY = ''
provider_url = 'https://rpc.bitlayer.org'
web3 = Web3(Web3.HTTPProvider(provider_url))


async def request_post(session: ClientSession, url, body=None, headers=None):
    async with await session.post(url, headers=headers, data=body) as response:
        response.raise_for_status()
        return response

async def request_get(session: ClientSession, url, headers=None):
    async with await session.get(url, headers=headers) as response:
        response.raise_for_status()
        return response

async def signature_key(text:str, private_KEY):
    signature = web3.eth.account.sign_message(encode_defunct(Web3.to_bytes(text=text)), f'0x{private_KEY}')
    signature_str = signature.signature.hex()
    return f'0x{signature_str}'


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
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}


async def main():
    async with aiohttp.ClientSession() as session:
        signature = await signature_key('BITLAYER', PRIVATE_KEY)
        print(signature)

        login_data = {"address": PUBLIC_KEY,
                "signature": signature}
        data = json.dumps(login_data)

        login_response = await request_post(session, 'https://www.bitlayer.org/me/login', data, headers)
        print(f"Login response: {login_response}")

        session_cookie =login_response.headers['Set-Cookie']
        headers['Cookie'] = session_cookie
        json_data = {
            'taskId': 1,
        }

        json_data_clime = {
            'taskId': 2,
            'taskType': 1,
        }

        signature_1 =await signature_key('fc33630f-3840-46dd-b8aa-66e48b93046b', PRIVATE_KEY)
        print(signature_1)
        return

        response = await request_post(session, 'https://www.bitlayer.org/me/task/start', json.dumps(json_data), headers)
        print(response)


        # Проверка активности
        can_receive_response = await request_get(session, 'https://api-activity.bitlayer.org/user-service/activity/popup/can_receive?address={PUBLIC_KEY}',headers)
        print(f"Can receive response: {can_receive_response}")

        # Пример дополнительного запроса
        activity_response = await request_get(session, 'GET', 'https://api-activity.bitlayer.org/activity/ready-player-one/v3/user?', headers)
        print(f"Activity response: {activity_response}")

        # Отправка отчета о выполнении задачи
        report_task_data = {
            'taskId': 1,
            'pageName': 'dapp_center'
        }
        report_task_response = await request_post(session, 'https://www.bitlayer.org/me/task/report',json.dumps(report_task_data), headers)
        print(f"Report task response: {report_task_response}")

        response = await request_post(session, 'https://www.bitlayer.org/me/task/claim', json.dumps(json_data_clime),headers)
        if (response.status == 200):
            print('ПОИНТЫ ЗАБРАЛ!')

#fc33630f-3840-46dd-b8aa-66e48b93046b подпись для 1 задачи внутри
if __name__ == '__main__':
    asyncio.run(main())
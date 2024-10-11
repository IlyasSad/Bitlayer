from web3 import Web3, AsyncHTTPProvider, AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware

def get_async_web3(provider_url, proxy=None):
    web3 = AsyncWeb3(AsyncHTTPProvider(provider_url, request_kwargs={"proxy": proxy}))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return web3

async def get_balance(provider_url, proxy=None, address=None):
    web3 = AsyncWeb3(AsyncHTTPProvider(provider_url, request_kwargs={"proxy": proxy}))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return await web3.eth.get_balance(address)

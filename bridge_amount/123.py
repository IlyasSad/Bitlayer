import requests

response = requests.post(
    "https://owlto.finance/api/bridge_api/v1/get_build_tx",
    headers={"Content-Type":"application/json"},
    json={
        "from_address":"0x3947d145c955727151D43E381e2521F73B5E4706",
        "from_chain_name":"BitlayerMainnet",
        "to_address":"0x3947d145c955727151D43E381e2521F73B5E4706",
        "to_chain_name":"BnbMainnet",
        "token_name":"USDT",
        "ui_value":"2"
    }
)
data = response.json()
print(data)
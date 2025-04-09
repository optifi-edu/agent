from src.checker import *

import os
import orjson
from dotenv import load_dotenv

load_dotenv()

class AgentWalletSync:
    def __init__(self):
        self.file_path = "./data/wallet.json"
        EDUCHAIN_RPC_URL = Web3.HTTPProvider(os.getenv("EDUCHAIN_RPC_URL"))
        self.w3 = Web3(EDUCHAIN_RPC_URL)
        self.admin_private_key=os.getenv("PRIVATE_KEY")

    def fetch_data(self, user_address):
        existing_data = self._load_existing_data()

        for entry in existing_data:
            if entry["user_address"] == user_address:
                private_key = entry["data"]
                
                return private_key

        print(f"No wallet data found for user address: {user_address}")
        return None
    
    def _get_token_ca(self, asset_id):
        match asset_id:
            case "edu":
                return "0x13BFA5eaE397e36593E788176C2FddcFffEC5075"
            case "wedu":
                return "0x89159C2A782ba2caE40Ec25C39A1f38397f1EED5"
            
    def _get_protocol_ca(self, protocol):
        match protocol:
            case "blendfinance":
                return "0x91F048130C88C1f759A9bdC19883559d3Dc275a6"
            case "sailfish":
                return "0xD95d2F7C38bfA2f9d7A618474Bc619470f01001F"
            case "camelot":
                return "0x763A03a3328e475f75EE2Dd0329b27F02EeD2443"
            case "edbank":
                return "0x4399B055b86C65bC2E91333D9118F98B974F052C"
            case "moveflow":
                return "0xf8C1cfD46A543EfB13305b041Fc573550207FA79"
    
    def swap(self, user_address, spender, token_in, token_out, amount):
        private_key = self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        amount_generalized = int(amount) * (10 ** 6)
        
        status = self.approve(sender_address, private_key, spender, token_in, amount)
        if status:
            abi = self._read_abi("./abi/OptiFinance.json")
            
            staking_contract = self.w3.eth.contract(address="0x54DDDE71d46409b919b8b29aD52133067B8441fb", abi=abi)
            nonce = self.w3.eth.get_transaction_count(sender_address)
            
            transaction = staking_contract.functions.swap(token_in, token_out, amount_generalized).build_transaction({
                'chainId': 656476,
                'gas': 1000000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return f"0x{tx_hash.hex()}"
        else:
            return f"Error during transaction"
    
    def approve(self, sender_address, private_key, spender, token_in, amount):
        try:
            approve_abi = self._read_abi("./abi/MockToken.json")
            amount = int(amount) * (10 ** 6)
            
            token_contract = self.w3.eth.contract(address=token_in, abi=approve_abi)
            nonce = self.w3.eth.get_transaction_count(sender_address)
            
            transaction = token_contract.functions.approve(spender, amount+10).build_transaction({
                'chainId': 656476,
                'gas': 1000000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return True
        
        except Exception as e:
            return False
    
    def stake(self, user_address, asset_id, protocol, spender, amount):
        approve_abi = self._read_abi("./abi/MockToken.json")
        amount = int(amount) * (10 ** 6)
        
        private_key = self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        contract_address = self._get_token_ca(asset_id)
        token_contract = self.w3.eth.contract(address=contract_address, abi=approve_abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.approve(spender, amount+10).build_transaction({
            'chainId': 656476,
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        #=========================================================
        
        abi = self._read_abi("./abi/MockStake.json")
        
        contract_address = self._get_protocol_ca(protocol)
        token_contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.stake(0, amount).build_transaction({
            'chainId': 656476,
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"
    
    
    def unstake(self, user_address, protocol):        
        abi = self._read_abi("./abi/MockStake.json")
        
        private_key = self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        contract_address = self._get_protocol_ca(protocol)
        token_contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.withdrawAll().build_transaction({
            'chainId': 656476,
            'gas': 1000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"


    def _read_abi(self, abi_path):
        with open(abi_path, 'r') as file:
            return orjson.loads(file.read())


    def _load_existing_data(self):
        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, 'rb') as file:
            return orjson.loads(file.read())

    def _save_data(self, data):
        with open(self.file_path, 'wb') as file:
            file.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))


def handle_user(user_address: str):
    user_risk = get_risk(user_address)
    user_staked = get_data_staked(user_address)
    
    match user_risk:
        case "low":
            handle_low_risk(user_address, user_staked)
        case "medium":
            handle_high_risk(user_address, user_staked)
        case "high":
            handle_high_risk(user_address, user_staked)


def handle_low_risk(user_address, user_staked):
    for i in range(len(user_staked)):
        protocol, response_raw = get_apy(filter='highest')
        result = handle_protocols(user_staked[i], protocol, response_raw)
        
        if result is None:
            continue

        from_protocol, token_ca, amount = result
        try:
            agent = AgentWalletSync()
            agent.unstake(user_address, from_protocol)
            agent.swap(user_address, spender="0x9F7b08e2365BFf594C4227752741Cb696B9b6E71", token_in=token_ca, token_out=protocol[2], amount=amount)
            agent.stake(user_address, protocol[2], protocol[0], amount)
            print("success")
        except Exception as e:
            print(e)
    

def handle_high_risk(user_address, user_staked):
    for i in range(len(user_staked)):
        protocol, response_raw = get_apy(filter='highest-best')
        result = handle_protocols(user_staked[i], protocol, response_raw)
        
        if result is None:
            continue

        from_protocol, token_ca, amount = result
        
        try:
            agent = AgentWalletSync()
            agent.unstake(user_address, from_protocol)
            agent.swap(user_address, spender="0x9F7b08e2365BFf594C4227752741Cb696B9b6E71", token_in=token_ca, token_out=protocol[2], amount=amount)
            agent.stake(user_address, protocol[2], protocol[0], amount)
            print("success")
        except Exception as e:
            print(e)


def get_apy(filter):
    result = requests.get('https://opti-edu-backend.vercel.app/staking')
    response = result.json()
    
    if filter == 'highest':
        protocol = [(item['addressStaking'], float(item['apy']), item['addressToken']) for item in response if item['stablecoin'] is True]
        highest_apy = max(protocol, key=lambda x: x[1])

        return highest_apy, response
    
    elif filter == 'highest-best':
        protocol = [(item['addressStaking'], float(item['apy']), item['addressToken']) for item in response]
        highest_apy = max(protocol, key=lambda x: x[1])

        return highest_apy, response
    

def handle_protocols(user_staked, protocol, response):
    for item in [user_staked]:
        protocol_address = item['protocol']
        if protocol_address != protocol[0]:
            token_ca = [item['addressToken'] for item in response if item['addressStaking'] == protocol_address][0]
            return item['protocol'], token_ca, item['amount']
    return None


def runner():
    with open('./data/wallet.json', 'rb') as file:
        existing_data =  orjson.loads(file.read())
        
    address_list = [item['user_address'] for item in existing_data]
    for address in address_list:
        handle_user(address)
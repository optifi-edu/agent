import os
import orjson
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

class AgentWallet:
    def __init__(self):
        self.file_path = "./data/wallet.json"
        EDUCHAIN_RPC_URL = Web3.HTTPProvider(os.getenv("EDUCHAIN_RPC_URL"))
        self.w3 = Web3(EDUCHAIN_RPC_URL)
        self.admin_private_key=os.getenv("PRIVATE_KEY")

    async def create_wallet(self, user_address):
        existing_data = await self._load_existing_data()
        
        for entry in existing_data:
            if entry["user_address"] == user_address:
                print(f"Wallet already exists for user address: {user_address}")
                return
        
        private_key = self.w3.eth.account.create()._private_key.hex()
        await self.save_wallet_data(private_key, user_address)
        

    async def save_wallet_data(self, private_key, user_address):
        output_data = {
            "user_address": user_address,
            "data": private_key
        }

        existing_data = await self._load_existing_data()
        existing_data.append(output_data)
        await self._save_data(existing_data)
        print("Wallet data saved successfully.")

    async def fetch_data(self, user_address):
        existing_data = await self._load_existing_data()

        for entry in existing_data:
            if entry["user_address"] == user_address:
                private_key = entry["data"]
                
                return private_key

        print(f"No wallet data found for user address: {user_address}")
        return None
    
    async def _check_address(self, user_address):
        private_key = await self.fetch_data(user_address)
        account = Web3().eth.account.from_key(private_key)
        return account.address
    
    async def _fund_wallet(self, user_address):
        private_key = await self.fetch_data(user_address)

        sender_address = self.w3.eth.account.from_key(self.admin_private_key).address
        receiver_address = self.w3.eth.account.from_key(private_key).address
        
        nonce = self.w3.eth.get_transaction_count(sender_address)
        transaction = {
            'to': receiver_address,
            'value': self.w3.to_wei(0.0001, 'ether'),
            'gas': 100000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'chainId': 656476,
        }

        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.admin_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"

    
    async def _transfer(self, user_address, amount, asset_id, destination):
        amount = amount * 10 ** 6
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(self.admin_private_key).address
        
        contract_address = await self._get_token_ca(asset_id)
        token_contract = self.w3.eth.contract(address=contract_address, abi=self._read_abi("abi/MockToken.json"))
    
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.transfer(destination, amount).build_transaction({
            'nonce': nonce,
            'gas': 100000000,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': 656476,
        })

        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"
    
    async def _get_token_ca(self, asset_id):
        match asset_id:
            case "edu":
                return "0x13BFA5eaE397e36593E788176C2FddcFffEC5075"
            case "wedu":
                return "0x89159C2A782ba2caE40Ec25C39A1f38397f1EED5"
    
    async def _get_protocol_ca(self, protocol):
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
    
    async def mint(self, user_address, asset_id, amount):
        amount = int(amount) * (10 ** 6)
        abi = await self._read_abi("./abi/MockToken.json")
        
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        contract_address = await self._get_token_ca(asset_id)
        token_contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.mint(sender_address, amount).build_transaction({
            'chainId': 656476,
            'gas': 100000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"
    
    async def transfer(self, user_address, contract_address, to, amount):
        amount = int(amount) * (10 ** 6)
        abi = await self._read_abi("./abi/MockToken.json")
        
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        token_contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.transfer(to, amount).build_transaction({
            'chainId': 656476,
            'gas': 100000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"
    
    async def swap(self, user_address, spender, token_in, token_out, amount):
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        amount_generalized = int(amount) * (10 ** 6)
        
        status = await self.approve(sender_address, private_key, spender, token_in, amount)
        if status:
            abi = await self._read_abi("./abi/OptiFinance.json")
            
            staking_contract = self.w3.eth.contract(address="0x54DDDE71d46409b919b8b29aD52133067B8441fb", abi=abi)
            nonce = self.w3.eth.get_transaction_count(sender_address)
            
            transaction = staking_contract.functions.swap(token_in, token_out, amount_generalized).build_transaction({
                'chainId': 656476,
                'gas': 100000000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return f"0x{tx_hash.hex()}"
        else:
            return f"Error during transaction"
    
    async def approve(self, sender_address, private_key, spender, token_in, amount):
        try:
            approve_abi = await self._read_abi("./abi/MockToken.json")
            amount = int(amount) * (10 ** 6)
            
            token_contract = self.w3.eth.contract(address=token_in, abi=approve_abi)
            nonce = self.w3.eth.get_transaction_count(sender_address)
            
            transaction = token_contract.functions.approve(spender, amount+10).build_transaction({
                'chainId': 656476,
                'gas': 100000000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return True
        
        except Exception as e:
            return False
    
    async def stake(self, user_address, asset_id, protocol, spender, amount):
        approve_abi = await self._read_abi("./abi/MockToken.json")
        amount = int(amount) * (10 ** 6)
        
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        contract_address = await self._get_token_ca(asset_id)
        token_contract = self.w3.eth.contract(address=contract_address, abi=approve_abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.approve(spender, amount+10).build_transaction({
            'chainId': 656476,
            'gas': 100000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        #=========================================================
        
        abi = await self._read_abi("./abi/MockStake.json")
        
        contract_address = await self._get_protocol_ca(protocol)
        token_contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.stake(0, amount).build_transaction({
            'chainId': 656476,
            'gas': 100000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"
    
    
    async def unstake(self, user_address, protocol):        
        abi = await self._read_abi("./abi/MockStake.json")
        
        private_key = await self.fetch_data(user_address)
        sender_address = self.w3.eth.account.from_key(private_key).address
        
        contract_address = await self._get_protocol_ca(protocol)
        token_contract = self.w3.eth.contract(address=contract_address, abi=abi)
        nonce = self.w3.eth.get_transaction_count(sender_address)
        
        transaction = token_contract.functions.withdrawAll().build_transaction({
            'chainId': 656476,
            'gas': 100000000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return f"0x{tx_hash.hex()}"


    async def _read_abi(self, abi_path):
        with open(abi_path, 'r') as file:
            return orjson.loads(file.read())


    async def _load_existing_data(self):
        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, 'rb') as file:
            return orjson.loads(file.read())

    async def _save_data(self, data):
        with open(self.file_path, 'wb') as file:
            file.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

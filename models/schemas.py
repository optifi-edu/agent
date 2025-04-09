from typing import Optional
from pydantic import BaseModel

class QueryRequestClassifier(BaseModel):
    data: str
    user_address: str

class QueryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    thread_id: str
    processing_time: float
    
class QueryUserWallet(BaseModel):
    user_address: str
    
class QueryMint(BaseModel):
    user_address: str
    asset_id: str
    amount: str
    
class QueryTransfer(BaseModel):
    user_address: str
    contract_address: str
    to: str
    amount: str
    
class QuerySwap(BaseModel):
    user_address: str
    spender: str
    token_in: str
    token_out: str
    amount: str
    
class QueryStake(BaseModel):
    user_address: str
    asset_id: str
    protocol: str
    spender: str
    amount: str
    
class QueryUnstake(BaseModel):
    user_address: str
    protocol: str
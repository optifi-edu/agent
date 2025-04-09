import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import aiohttp
import pandas as pd
import orjson
from fastapi import HTTPException
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
from langchain.tools import Tool
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper




class CdpAgent:
    def __init__(self, url: str, max_workers: int = 3):
        self.url = url
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.agent_executor = None
        self._lock = asyncio.Lock()
        self.knowledge_data = []
    
    async def fetch_knowledge(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                if response.status == 200:
                    self.knowledge_data = await response.json()
                else:
                    raise HTTPException(status_code=response.status, detail=f"Failed to fetch {self.url}")

    async def initialize(self):
        async with self._lock:
            await self.fetch_knowledge()
            retriever = await self.create_retriever()
            self.agent_executor = await asyncio.get_event_loop().run_in_executor(
                self.thread_pool,
                self._sync_initialize_agent,
                retriever
            )

    async def create_retriever(self):
        df = pd.DataFrame(self.knowledge_data)
        docs = [
            Document(
                page_content=f"IdProject: {row['idProtocol']}, Chain: {row['chain']}, Symbol: {row['nameToken']}, TVL: {row['tvl']}, APY: {row['apy']}, Stablecoin: {row['stablecoin']}",
                metadata={"symbol": row["nameToken"], "protocol": row["idProtocol"]}
            )
            for _, row in df.iterrows()
        ]

        return await asyncio.get_event_loop().run_in_executor(
            self.thread_pool,
            lambda: FAISS.from_documents(docs, OpenAIEmbeddings()).as_retriever()
        )

    def _sync_initialize_agent(self, retriever):
        llm = ChatOpenAI(model="gpt-4o-mini-2024-07-18")
        qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
        qa_tool = Tool(
            name="KnowledgeBaseQA",
            func=lambda query: qa_chain.run(query),
            description="Use this to search for TVL, APY, or DeFi information.",
        )

        agentkit = CdpAgentkitWrapper()
        cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(agentkit)
        
        tools = cdp_toolkit.get_tools()
        tools.append(qa_tool)
        
        return create_react_agent(llm, tools=tools)

    async def process_query(self, query: str, thread_id: Optional[str] = None):
        await self.initialize()
        config = {"configurable": {"thread_id": thread_id or "CDP Agent API"}}
        return await asyncio.get_event_loop().run_in_executor(
            self.thread_pool,
            lambda: self.agent_executor.invoke(
                {"messages": [HumanMessage(content=query)]},
                config=config
            )["messages"][-1].content
        )




class CdpAgentClassifier:
    def __init__(self, max_workers: int = 3):
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.agent_executor = None
        self._lock = asyncio.Lock()
        self.file_path = "./data/wallet.json"

    async def initialize(self):
        async with self._lock:
            if self.agent_executor is None:
                self.agent_executor = await asyncio.get_event_loop().run_in_executor(
                    self.thread_pool,
                    self._sync_initialize_agent
                )

    def _sync_initialize_agent(self):
        llm = ChatOpenAI(model="gpt-4o-mini-2024-07-18")
        memory = MemorySaver()
        
        return create_react_agent(
            llm,
            tools=[],
            checkpointer=memory,
            state_modifier=(
                "You are a risk profile classifier that evaluates users based on their responses to investment-related questions. "
                "You MUST ALWAYS respond in valid JSON format with a single 'risk' key with value being either 'low', 'medium', or 'high'. "
                "When analyzing responses, consider factors like: age, investment experience, financial goals, time horizon, and risk tolerance. "
                "Base your classification on standard risk assessment principles. "
                "Sample questions you should expect and factor into your analysis: "
                "1. How do you feel about potential losses in staking investments? "
                "2. How long are you willing to lock up your staked assets? "
                "3. How do you assess smart contract security before staking? "
                "4. What is your approach to diversification in staking? "
                "5. How do you react to market fluctuations affecting your staked assets? "
                "Regardless of the input format, ALWAYS respond with: {\"risk\": \"risk_level\"} where risk_level is low, medium, or high"
            ),
        )

    async def process_query(self, query: str, user_address: str):
        if self.agent_executor is None:
            raise RuntimeError("Agent not initialized. Please call initialize() first.")
            
        config = {"configurable": {"thread_id": "Risk Assessment API"}}
        
        response =  await asyncio.get_event_loop().run_in_executor(
            self.thread_pool,
            lambda: self.agent_executor.invoke(
                {"messages": [HumanMessage(content=query)]},
                config=config
            )["messages"][-1].content
        )
        
        self._update_risk_profile(self._parse_risk(response), user_address)
        
        return response
    
    def _update_risk_profile(self, risk_profile: str, user_address: str):
        with open(self.file_path, 'rb') as file:
            wallet_data = orjson.loads(file.read())
            
        for entry in wallet_data:
            if entry["user_address"] == user_address:
                entry["risk_profile"] = risk_profile
                with open(self.file_path, 'wb') as file:
                    file.write(orjson.dumps(wallet_data, option=orjson.OPT_INDENT_2))
                
    def _parse_risk(self, response):
        return orjson.loads(response).get("risk")
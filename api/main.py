from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from uuid import uuid4
from config import CHECKPOINT_DB
from core.database import init_db , seed_products
from vectordb.store import build_vector_store
from graph.main_graph import build_main_graph
from typing import Literal
from langgraph.checkpoint.memory import MemorySaver

compiled_graph = None
checkpointer_connection = None

@asynccontextmanager
async def lifespan(app:FastAPI):
    global compiled_graph, checkpointer_connection

    await init_db()
    await seed_products()
    await build_vector_store()

    #opening a connection with AsyncSqliteSaver
    print(">>> Vector store done, opening checkpoint connection")
    checkpointer_connection = await aiosqlite.connect(CHECKPOINT_DB)
    #creating a saver by passing connection 
    # saver = AsyncSqliteSaver(checkpointer_connection)
    saver = MemorySaver()
    print(">>> Saver created")

    #compiling the mainframe
    compiled_graph = build_main_graph(checkpointer=saver)
    print("############# Firing up Ecommerce Agent ###############")

    yield

    await checkpointer_connection.close()
    print("############### Killing Ecommerce Agent ###################")


#creating FASTAPI app
app = FastAPI(lifespan=lifespan)

#request model 
class OrderRequest(BaseModel):
    customer_id : str
    raw_input : str
    product_id : str
    payment_expiry : str
    shipping_zone: Literal["domestic", "international"]


#the endpoint
@app.post("/order")
async def create_order(request:OrderRequest):
    order_id = f"ORD-{uuid4().hex[:8]}"
    thread_id = order_id

    initial_state = {   
                        "order_id" : order_id,
                        "customer_id" : request.customer_id,
                        "raw_input" : request.raw_input,
                        "product_id" : request.product_id ,
                        "payment_expiry": request.payment_expiry,    
                        "shipping_zone": request.shipping_zone,
                        "status" : "pending",
                        "messages" : []    
                    }

    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = await compiled_graph.ainvoke(initial_state, config=config)
        return result
    except Exception as e:
        raise HTTPException(status_code = 500, detail = str(e))
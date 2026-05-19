#Defining A2A contracts : Pydantic Schemas
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import uuid4

class A2AMessage(BaseModel):
    message_id : str = Field(default_factory= lambda : str(uuid4())) # unique ID for tracing 
    timestamp : datetime = Field(default_factory= datetime.utcnow) # when was it sent 
    sender : str # which agent sends the message
    receiver : str # which agent receives it 

class InventoryQuery(A2AMessage):   # State contract between Order Agent-------->Inventory Agent 
    message_type : Literal["inventory_query"] = "inventory_query"
    product_id : Optional[str] = None
    product_name : Optional[str] = None 
    quantity_requested : int 
    allow_alternatives : bool = True

class StockResponse(A2AMessage): # State contract between Inventory Agent --------> Order Agent 
    message_type : Literal["stock_response"] = "stock_response"
    product_id : str
    product_name : str
    quantity_available : int 
    is_available : bool 
    is_low_stock : bool 
    alternative_products : list[dict] = []
    unit_price : float 

class OrderConfirm(A2AMessage): # State Contract between Order Agent and Delivery Agent 
    message_type : Literal["order_confirm"] = "order_confirm"
    order_id : str
    customer_id : str
    product_id : str
    quantity : int 
    total_amount : float
    shipping_zone : Literal["domestic", "international"]
    payment_validated : bool 
    fraud_flagged : bool 

class StatusUpdate(A2AMessage) : #State contract between Delivery Agent 
    message_type :Literal["status_update"] = "status_update"
    order_id : str
    status : Literal["pending", "fulfilled", "shipped", "delivered", "returned"]
    carrier : str
    eta_days : int
    notes : Optional[str] = None 
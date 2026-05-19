from typing_extensions import TypedDict
from typing import Annotated, Optional, Literal
from operator import add

# ORDER STATE
class OrderState(TypedDict):
    # order details 
    order_id: str
    customer_id: str
    product_id: str
    product_name: str
    quantity: int 
    total_amount: float
    shipping_zone: Literal["domestic", "international"]
    raw_input: str
    payment_expiry: str

    # state machine position
    status: Literal["pending", "fulfilled", "shipped", "delivered", "returned", "rejected"]

    # A2A message history
    messages: Annotated[list, add]

    # snapshots from each agent
    inventory_response: Optional[dict]
    order_confirmation: Optional[dict]
    delivery_update: Optional[dict]

    # business rule flags 
    fraud_flagged: bool 
    payment_valid: bool 
    low_stock_alert: bool 

    # error tracking 
    error: Optional[str]
    retry_count: int


# INVENTORY STATE (Invetory Subgraph)
class InventoryState(TypedDict):
    product_name : str
    product_id : str
    quantity : int
    inventory_response : Optional[dict] 
    low_stock_alert : bool
    messages : Annotated[list, add]
    
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from datetime import datetime
import json
from core.schemas import InventoryQuery, OrderConfirm
from core.state import OrderState

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

async def parse_order(query: str):
    system_prompt = """
                        You are an order parser for an E commerce platform. 
                        You have to take the query of customer as input and extract from the query the name of the product requested by the customer 
                        and quantiy of the product requested by the customer. 
                        Incase the quantity is not specified please assume the quantity as 1 
                        
                        Once extraction is complete please ensure your output is an JSON object in the following format. 

                        Output Format : 
                        {"product_name" : "...", "quantity" : integer}
                    """
    
    response = await llm.ainvoke([SystemMessage(system_prompt), HumanMessage(query)])
    parsed = json.loads(response.content)
    return parsed


def validate_payment(expiry_str:str):
    expiry_date = datetime.strptime(expiry_str, "%m/%y")

    if expiry_date > datetime.today():
        return True
    else:
        return False
    

def check_fraud(total_amount: float, quantity:int):
    if total_amount>200000:
        return True
    elif quantity > 10 :
        return True
    elif total_amount > 50000 and quantity>5:
        return True
    else:
        return False
    

async def order_agent_1(state: OrderState):
    parsed_order = await parse_order(state["raw_input"])
    
    inventory_query = InventoryQuery(
                                     sender= "order_agent",
                                     receiver= "inventory_agent", 
                                     product_name= parsed_order["product_name"],
                                     quantity_requested= int(parsed_order["quantity"])
                                    )


    return { 
            "product_name" : inventory_query.product_name,
            "quantity" : int(inventory_query.quantity_requested),
            "messages" : [inventory_query.model_dump()]
           }


async def order_agent_2(state: OrderState):

    if validate_payment(state["payment_expiry"]): 
        payment_valid = True
    else:
        payment_valid = False

    if check_fraud(state["quantity"]*state["inventory_response"]["unit_price"], state["quantity"]):
        fraud = True
    else:
        fraud = False
    
    status = "fulfilled" if (payment_valid and not fraud and state['inventory_response']["is_available"]) else "rejected"  


    order_id = state["order_id"]
    customer_id = state["customer_id"]
    product_id = state["product_id"]
    quantity = state["quantity"]
    total_amount = state["quantity"]*state["inventory_response"]["unit_price"]
    shipping_zone = state["shipping_zone"]

    order_confirm = None

    if status == "fulfilled": 
        order_confirm = OrderConfirm(
                                    sender = "order_agent", 
                                    receiver= "delivery_agent",  
                                    order_id=order_id,
                                    customer_id=customer_id,
                                    product_id = product_id,
                                    quantity=quantity,
                                    total_amount = total_amount,
                                    shipping_zone= shipping_zone,
                                    payment_validated=payment_valid,
                                    fraud_flagged=fraud,
                                    )
    

    
    return {
            "fraud_flagged" : fraud,
            "payment_valid" : payment_valid,
            "status" : status,
            "total_amount" : total_amount,
            "order_confirmation": order_confirm.model_dump() if order_confirm else None,
            "messages": [order_confirm.model_dump()] if order_confirm else [],
            "inventory_available": state["inventory_response"]["is_available"],

    }
    

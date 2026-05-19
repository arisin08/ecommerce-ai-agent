from datetime import datetime
from core.state import OrderState
from core.schemas import  StatusUpdate


def assign_carrier(shipping_zone:str):
    if shipping_zone == "domestic":
        return "Bluedart"
    else: 
        return "DHL"

def calculate_eta(shipping_zone): 
    if shipping_zone == "domestic":
        return 3
    else:
        return 10 
    
def check_return_eligibility(delivery_date: datetime):
    timedelta = datetime.today() - delivery_date
    if timedelta.days <=30:
        return True
    else:
        return False
    
async def delivery_agent(state: OrderState):
    print("============= Delivery Agent tracking your order ==============")

    order_confirm = state.get("order_confirmation")
    carrier = assign_carrier(state["shipping_zone"])
    eta = calculate_eta(state["shipping_zone"])

    #Building StatusUpdate (A2A contract b/w Order and  Delivery Agent)
    status_update = StatusUpdate(
                                  sender = "delivery_agent",
                                  receiver = "customer",
                                  order_id = state["order_id"],
                                  status= "shipped",
                                  carrier = carrier, 
                                  eta_days = eta,
                                  notes = f"Order shipped via {carrier}. ETA {eta} day(s). Returns accepted within 30 days of delivery."

                                )
    
    return {
            "delivery_update" : status_update.model_dump(),
            "status" : status_update.status,
            "messages" : [status_update.model_dump()]
    }
    
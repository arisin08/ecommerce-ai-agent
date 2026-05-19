from core.database import AsyncSessionLocal, Product
from sqlalchemy import select
from vectordb.store import semantic_search
from core.state import InventoryState
from core.schemas import StockResponse

#checks the inventory vector database and return the product object 
async def check_stock(product_id : str= None, product_name: str=None):
    async with AsyncSessionLocal() as session: 
        if product_id:
            result= await session.execute(select(Product).where(Product.id == product_id))
        elif product_name:
            result= await session.execute(select(Product).where(Product.name == product_name))
        else:
            return None
        return result.scalar_one_or_none()

#checks current stock quantity against max stock quantity and flags low stock scenarios  
def is_low_stock(product: Product):
    if product.quantity/product.max_stock<0.10 :
        return True
    else:
        return False

async def inventory_agent(state:InventoryState):
    print("============= Inventory Agent rummaging through our store ==============")
    
    #querying inventory
    inventory_product = await check_stock(product_id=state["product_id"], product_name=state["product_name"])

    alternatives = []
    
    if not inventory_product:
        is_available = False 
        quantity_available = 0
        unit_price = 0.0
        low_stock = False
        alternatives = await semantic_search(state["product_name"])

    else:
        is_available = inventory_product.quantity>=state['quantity']
        quantity_available = inventory_product.quantity
        unit_price = inventory_product.unit_price
        low_stock =   is_low_stock(inventory_product)

        if not is_available or low_stock:
            alternatives = await semantic_search(state["product_name"])
        
    #Building StockResponse (A2A contract b/w Order and Inventory Agent)
    stock_response = StockResponse(
                                    sender= "inventory_agent", 
                                    receiver = "order_agent",
                                    product_id= state["product_id"],
                                    product_name = state["product_name"],
                                    quantity_available = quantity_available,
                                    is_available = is_available,
                                    is_low_stock = low_stock,
                                    alternative_products = alternatives,
                                    unit_price = unit_price  
                                  )
    
    return {
            "inventory_response" : stock_response.model_dump(),
            "low_stock_alert" : stock_response.is_low_stock,
            "total_amount" : stock_response.quantity_available * stock_response.unit_price,
            "messages" : [stock_response.model_dump()]
    }

    
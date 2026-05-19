from langgraph.graph import StateGraph , START, END 
from core.state import OrderState
from graph.inventory_graph import inventory_agent_compiled
from agents.order import order_agent_1, order_agent_2
from agents.delivery import delivery_agent

#Router function after Order Agent 2 node 
def router(state:OrderState):
    if state["status"] == "rejected":
        return END
    else:
        return "delivery_agent"

#creating graph object with OrderState
main_graph = StateGraph(OrderState)

#adding Nodes
main_graph.add_node("order_agent_1", order_agent_1)
main_graph.add_node("inventory_agent", inventory_agent_compiled)
main_graph.add_node("order_agent_2", order_agent_2)
main_graph.add_node("delivery_agent", delivery_agent)

#adding edges 
main_graph.add_edge(START, "order_agent_1")
main_graph.add_edge("order_agent_1", "inventory_agent")
main_graph.add_edge("inventory_agent", "order_agent_2")
main_graph.add_conditional_edges("order_agent_2", router, {END:END, "delivery_agent":"delivery_agent"})
main_graph.add_edge("delivery_agent", END)

def build_main_graph(checkpointer):
    return main_graph.compile(checkpointer = checkpointer)

graph = main_graph.compile()
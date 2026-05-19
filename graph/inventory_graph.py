from langgraph.graph import StateGraph , START, END 
from core.state import InventoryState
from agents.inventory import inventory_agent

#Initializing Graph with state
inventory_agent_graph = StateGraph(InventoryState)

#building nodes and edges 
inventory_agent_graph.add_node("inventory_agent_node", inventory_agent)
inventory_agent_graph.add_edge(START, "inventory_agent_node")
inventory_agent_graph.add_edge("inventory_agent_node", END)

#compiling the graph
inventory_agent_compiled = inventory_agent_graph.compile()



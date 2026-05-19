# E-Commerce Multi-Agent Fulfillment System

A production-ready, stateful multi-agent system that automates end-to-end e-commerce order fulfillment. You send it a raw customer request like "I want 2 gaming laptops" and it handles everything — checking stock, validating payment, catching fraud, assigning a carrier, and returning a fully traced order confirmation. Built with LangGraph for orchestration, FastAPI for the HTTP layer, and LangSmith for observability.

---

## Architecture

```
POST /order
     │
     ▼
order_agent_1          →  parses raw customer input via LLM
     │
     ▼
inventory_subgraph     →  queries SQLite for real stock counts
     │                    falls back to ChromaDB semantic search if OOS
     ▼
order_agent_2          →  fraud check + payment validation (deterministic)
     │
     ├── rejected ──────→  END (no delivery)
     │
     └── fulfilled ─────→  delivery_agent
                                │
                                ▼
                           assigns carrier + ETA
                                │
                                ▼
                              END
```

Every message between agents is a validated Pydantic schema. Every run is checkpointed to SQLite so orders survive crashes. Every LLM call is traced in LangSmith.

---

## Tech Stack

| Technology | Why |
|---|---|
| **LangGraph** | Stateful graph orchestration with conditional routing and subgraph support |
| **LangChain + OpenAI** | LLM integration for order parsing — the only non-deterministic step |
| **FastAPI** | Async HTTP layer with lifespan management for compile-once startup |
| **SQLAlchemy + aiosqlite** | Async ORM for inventory — deterministic stock reads, no hallucination |
| **ChromaDB + OpenAI Embeddings** | Semantic product search for out-of-stock alternatives |
| **Pydantic** | Runtime-validated A2A message contracts between agents |
| **LangSmith** | Full observability — every agent run, LLM call, token count, and latency |
| **AsyncSqliteSaver** | DB-backed checkpointing for crash recovery and order resumption |

---

## Agent Design

**Order Agent (Part 1)** — Takes raw customer input and uses an LLM to extract product name and quantity. Emits a validated `InventoryQuery` message and passes structured data to the next stage.

**Inventory Agent (Subgraph)** — Queries SQLite for real-time stock counts. Never uses an LLM for stock data — all reads are deterministic. If a product is out of stock or below the 10% low-stock threshold, it triggers a ChromaDB semantic search to find similar in-stock alternatives. Returns a `StockResponse` with full product details.

**Order Agent (Part 2)** — Applies business rules against the inventory response. Runs a multi-signal fraud check (order value, quantity, combined thresholds) and validates payment expiry. Emits an `OrderConfirm` if the order passes, or sets status to `rejected` if it fails. The graph router reads this status to decide whether to continue to delivery.

**Delivery Agent** — Assigns a shipping carrier based on zone (BlueDart for domestic, DHL for international), calculates ETA (3 days domestic, 10 days international), and emits a `StatusUpdate` with return eligibility noted. Runs only on fulfilled orders.

---

## A2A Protocol

Agents communicate exclusively through Pydantic-validated message schemas — no loose dictionaries passed between nodes. Every message has a `message_id`, `timestamp`, `sender`, and `receiver` for full audit traceability.

```
InventoryQuery     →  Order Agent → Inventory Agent
StockResponse      →  Inventory Agent → Order Agent
OrderConfirm       →  Order Agent → Delivery Agent
StatusUpdate       →  Delivery Agent → State
```

The complete message chain is stored in the `messages` field of the order state, giving you a timestamped record of every agent decision for any given order.

The key architectural decision: the LLM is only involved in `order_agent_1` for language parsing. Every other decision — stock counts, fraud flags, payment validation, carrier assignment — is deterministic. This prevents inventory hallucination and keeps business logic auditable.

---

## Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd ecommerce-fulfillment

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and fill in your API keys
```

Your `.env` file needs:

```
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=ls-...
LANGSMITH_TRACING_V2=true
LANGSMITH_PROJECT=fulfillment-system
```

```bash
# 5. Start the server
uvicorn api.main:app --reload
```

On startup the server will:
- Initialize the SQLite inventory database
- Seed it with 5 test products if empty
- Load the ChromaDB vector store from disk (or build it fresh on first run)
- Compile the LangGraph with a SQLite checkpointer
- Print `Firing up Ecommerce Agent` when ready

---

## API

### `POST /order`

**Request:**
```json
{
  "customer_id": "CUST-001",
  "raw_input": "I want 1 Gaming Laptop Pro",
  "product_id": "P001",
  "payment_expiry": "12/26",
  "shipping_zone": "domestic"
}
```

**Response (fulfilled order):**
```json
{
  "order_id": "ORD-553df730",
  "status": "shipped",
  "carrier": "Bluedart",
  "eta_days": 3,
  "fraud_flagged": false,
  "payment_valid": true,
  "total_amount": 130000,
  "order_confirmation": { ... },
  "delivery_update": { ... },
  "messages": [ ... ]
}
```

The `messages` array contains the full A2A audit trail — every schema exchanged between agents, in order, with timestamps.

---

## Test Products

| ID | Product | Stock | Notes |
|---|---|---|---|
| P001 | Gaming Laptop Pro | 45 | Normal stock |
| P002 | Budget Laptop Pro | 60 | Normal stock |
| P003 | Kreo Hive Keyboard | 30 | Normal stock |
| P004 | Logitech MX4 Mouse | 3 | Low stock (triggers alert) |
| P005 | LG P11 Monitor | 0 | Out of stock (triggers VDB fallback) |

---

## Project Structure

```
ecommerce-fulfillment/
│
├── config.py                  ← all environment config in one place
├── requirements.txt
├── README.md
│
├── core/
│   ├── schemas.py             ← Pydantic A2A message contracts
│   ├── state.py               ← LangGraph TypedDict state definitions
│   └── database.py            ← SQLAlchemy models, init, seed
│
├── vectordb/
│   └── store.py               ← ChromaDB setup + semantic search
│
├── agents/
│   ├── inventory_agent.py     ← stock check, low stock detection, VDB fallback
│   ├── order_agent.py         ← LLM parsing, fraud check, payment validation
│   └── delivery_agent.py      ← carrier assignment, ETA, return eligibility
│
├── graph/
│   ├── inventory_graph.py     ← compiled inventory subgraph
│   └── main_graph.py          ← main graph + router + build function
│
├── api/
│   └── main.py                ← FastAPI app, lifespan, POST /order endpoint
│
└── scripts/
    └── simulate.py            ← load test simulation
```

---

## Observability

All runs are traced in LangSmith under the `fulfillment-system` project. For each order you can see the full execution waterfall, every agent's input and output state, the exact LLM prompt and response, token counts, and per-node latency.

Typical performance on a single order:
- Total latency: ~2.7s
- LLM portion: ~2.6s (96% of total)
- DB + logic: <100ms
- Cost per order: <$0.0001

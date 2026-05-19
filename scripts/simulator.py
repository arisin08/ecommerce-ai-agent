import asyncio
import httpx
import random
import time
from uuid import uuid4
from collections import Counter
import csv
from pathlib import Path
from datetime import datetime


API_URL = "http://127.0.0.1:8000/order"
SIMULATION_ID = datetime.now().strftime("sim_%Y%m%d_%H%M%S")
RESULTS_FILE = Path("simulation_results.csv")

TOTAL_ORDERS = 100
CONCURRENT_BATCH = 2


def generate_order_payload():
    customer_id = f"CUST-{uuid4().hex[:6]}"

    items = [
                "Happy Orders",
                "Out-of-stock Orders",
                "Fraud Orders",
                "Expired payement Orders",
                "International Orders"
            ]

    select = random.choices(
        items,
        weights=[7, 1, 1, 0.5, 0.5],
        k=1
    )

    initial_state = {}

    if select[0] == "Happy Orders":
        n = random.choice([1, 2])

        initial_state = {
            "customer_id": customer_id,
            "raw_input": f"I want {n} gaming laptops",
            "product_id": "P001",
            "payment_expiry": "12/26",
            "shipping_zone": "domestic",

        }

    elif select[0] == "Out-of-stock Orders":

        initial_state = {
            "customer_id": customer_id,
            "raw_input": "I want 4k gaming monitor",
            "product_id": "P005",
            "payment_expiry": "12/26",
            "shipping_zone": "domestic",
        }

    elif select[0] == "Fraud Orders":

        initial_state = {
            "customer_id": customer_id,
            "raw_input": "I want 15 gaming laptops",
            "product_id": "P001",
            "payment_expiry": "10/26",
            "shipping_zone": "domestic",
        }

    elif select[0] == "Expired payement Orders":

        initial_state = {
            "customer_id": customer_id,
            "raw_input": "I want 1 keyboard",
            "product_id": "P004",
            "payment_expiry": "10/20",
            "shipping_zone": "domestic",
        }

    elif select[0] == "International Orders":

        initial_state = {
            "customer_id": customer_id,
            "raw_input": "I want 2 mouse",
            "product_id": "P003",
            "payment_expiry": "10/28",
            "shipping_zone": "international",
        }

    return initial_state
    
async def wait_for_server(client, retries=10, delay=2):
    for _ in range(retries):
        try:
            await client.get("http://127.0.0.1:8000/docs")
            return
        except Exception:
            await asyncio.sleep(delay)
    raise RuntimeError("Server not ready")

async def send_order(client, payload):

    start_time = time.time()

    try:

        response = await client.post(API_URL, json=payload)

        latency = time.time() - start_time

        result = response.json()

        return {
            "status_code": response.status_code,
            "final_status": result.get("status"),
            "latency": latency
        }

    except Exception as e:

        latency = time.time() - start_time

        return {
                "status_code": 0,
                "final_status": "error",
                "latency": latency,
                "error": f"{type(e).__name__}: {repr(e)}"
               }
    
async def send_order_with_retry(client, payload, retries=1):
    for attempt in range(retries + 1):
        result = await send_order(client, payload)
        if result["final_status"] != "error" or attempt == retries:
            return result
        await asyncio.sleep(1)

async def run_simulation():

    all_results = []

    start = time.time()

    async with httpx.AsyncClient(timeout=120) as client:
        await wait_for_server(client)
        for batch_start in range(0, TOTAL_ORDERS, CONCURRENT_BATCH):

            tasks = []

            for _ in range(CONCURRENT_BATCH):

                payload = generate_order_payload()

                tasks.append(send_order_with_retry(client, payload))

            batch_results = await asyncio.gather(*tasks)

            all_results.extend(batch_results)
            await asyncio.sleep(0.25)

            print(f"Completed {len(all_results)}/{TOTAL_ORDERS}")

    total_time = time.time() - start

    successes = [r for r in all_results if r["status_code"] == 200]

    failures = [r for r in all_results if r["status_code"] != 200]

    avg_latency = (sum(x["latency"]  for x in all_results) / len(all_results))

    status_dist = Counter(x["final_status"] for x in all_results)

    print("\n"+"="*50)
    print("SIMULATION RESULTS")
    print("="*50)

    print(f"Total Orders: {TOTAL_ORDERS}")

    print(f"Success: {len(successes)}")

    print(f"Failed: {TOTAL_ORDERS-len(successes)}")
    print(f"Average latency: {avg_latency:.3f}s")

    print(f"Total runtime: {total_time:.2f}s")

    print("\nStatus distribution:")

    for k,v in status_dist.items():
        print(f"{k}: {v}")

    # ---------- ERROR DEBUGGING ---------- #

    if failures:
        print("\nSample Errors:")
        for failure in failures[:5]:
            print(failure.get("error", f"HTTP {failure['status_code']}"))
    
    sorted_latencies = sorted(r["latency"] for r in all_results)
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
    print(f"p95 latency: {p95:.3f}s")


    print(f"Throughput: {TOTAL_ORDERS/total_time:.2f} orders/sec")

if __name__ == "__main__":
    asyncio.run(run_simulation())

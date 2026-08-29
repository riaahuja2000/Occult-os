import asyncio
import time
from motor.motor_asyncio import AsyncIOMotorClient

async def run_benchmark():
    # Setup
    client = AsyncIOMotorClient()
    db = client.test_db_perf

    # Clean up first
    await db.knowledge_entries.delete_many({})
    await db.kb_files.delete_many({})

    # Insert dummy data
    entries = [{"deleted_at": None, "created_at": i, "topic": f"topic_{i%10}", "data": "x"*1000} for i in range(500)]
    files = [{"deleted_at": None, "created_at": i, "filename": f"file_{i}", "data": "y"*1000} for i in range(200)]

    if entries:
        await db.knowledge_entries.insert_many(entries)
    if files:
        await db.kb_files.insert_many(files)

    # Baseline
    start = time.perf_counter()
    for _ in range(100):
        found_entries = await db.knowledge_entries.find({"deleted_at": None}).sort("created_at", -1).to_list(500)
        for e in found_entries:
            e.pop("_id", None)

        found_files = await db.kb_files.find({"deleted_at": None}).sort("created_at", -1).to_list(200)
        for f in found_files:
            f.pop("_id", None)
    end = time.perf_counter()
    baseline_time = end - start
    print(f"Baseline (manual pop): {baseline_time:.4f} seconds")

    # Optimized
    start = time.perf_counter()
    for _ in range(100):
        found_entries = await db.knowledge_entries.find({"deleted_at": None}, {"_id": 0}).sort("created_at", -1).to_list(500)
        found_files = await db.kb_files.find({"deleted_at": None}, {"_id": 0}).sort("created_at", -1).to_list(200)
    end = time.perf_counter()
    optimized_time = end - start
    print(f"Optimized (projection): {optimized_time:.4f} seconds")
    print(f"Improvement: {((baseline_time - optimized_time) / baseline_time * 100):.2f}%")

if __name__ == "__main__":
    asyncio.run(run_benchmark())

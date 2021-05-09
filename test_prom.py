import asyncio
import os
import sys

# For now.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/src")

from code_deck import kubernetes, prometheus


async def main():
    await kubernetes.load_all()
    values = await prometheus.dev.range("sum(container_memory_working_set_bytes)")
    print(values)


asyncio.run(main())

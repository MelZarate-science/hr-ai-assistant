import asyncio
import sys
import os
sys.path.append(os.getcwd())

from app.main import ask_hr
from app.routes import QueryRequest

async def test():
    r = QueryRequest(query='¿Cómo se hace una pizza?', history=[])
    resp = await ask_hr(r)
    print(f'Respuesta: {resp.answer}')
    print(f'Error: {resp.error}')

if __name__ == "__main__":
    asyncio.run(test())

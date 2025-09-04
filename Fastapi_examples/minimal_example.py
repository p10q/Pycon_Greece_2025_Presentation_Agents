# main.py

from fastapi import FastAPI

app = FastAPI()  # Here we define our ASGI app here
# Which is native to FastAPI and asynchronous by default
# This allows us to handle requests concurrently and efficiently


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}


# @app.get("/") declares an endpoint that responds to GET requests on the root path and returns JSON

# The second endpoint demonstrates path parameters (item_id: int) and an optional query parameter q

# Explain optional asynchronous handlers.
# FastAPI supports both synchronous and asynchronous request handlers
# By default, request handlers are synchronous (def read_item)
# If you want to use asynchronous code (e.g., for database calls), you can define
# your handler as async def read_item
# FastAPI will handle the async/await syntax properly, allowing for non-blocking I/O
# This is useful for high-performance applications that need to handle many requests concurrently

# If the code needs concurrency, you can use async def instead of def—FastAPI will handle async/await properly

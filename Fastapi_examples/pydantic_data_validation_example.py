from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


class Item(BaseModel):
    name: str  # Required field
    price: float  # Required fielda
    is_offer: bool | None = None  # Optional field with default value None


@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}


# FastAPI automatically validates the request body against the Item model and returns clear errors if the client sends invalid data

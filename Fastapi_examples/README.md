# FastAPI Examples

This directory contains practical FastAPI examples designed for the PyCon 2025 Greece tutorial on building AI-powered web services.

## 🚀 Quick Start (90 seconds demo)

### Prerequisites
```bash
python -m venv .venv

pip install fastapi uvicorn "pydantic[email]"
```

### Run the Examples

#### 1. Minimal Example
```bash
cd Fastapi_examples
uvicorn minimal_example:app --reload
```
Open: http://localhost:8000

#### 2. Pydantic Data Validation Example  
```bash
cd Fastapi_examples
uvicorn pydantic_data_validation_example:app --reload
```
Open: http://localhost:8000/docs

## 📖 Examples Overview

### `minimal_example.py`
**Duration: ~60 seconds**

A basic FastAPI application demonstrating:
- Simple GET endpoints
- Path parameters (`/items/{item_id}`)  
- Query parameters (`?q=something`)
- JSON responses
- Type hints for automatic validation

**Key Learning Points:**
- FastAPI automatically generates OpenAPI docs
- Type hints provide automatic validation
- Async support is built-in

### `pydantic_data_validation_example.py`  
**Duration: ~90 seconds**

A comprehensive user management API showcasing:
- **Pydantic Models**: Request/response validation with `UserCreate`, `UserResponse`, `UpdateUser`
- **Data Validation**: Email validation, age constraints, field length limits
- **HTTP Methods**: GET, POST, PUT, DELETE
- **Async Operations**: Simulated database operations with `async/await`
- **Error Handling**: HTTP exceptions with meaningful messages
- **Query Parameters**: Pagination with `skip` and `limit`
- **Status Codes**: Proper HTTP status codes (201 for creation, 404 for not found)

## 🎯 Live Demo Script

### Minimal Example Demo (60 seconds)
1. **Start server**: `uvicorn minimal_example:app --reload`
2. **Show auto-docs**: Navigate to http://localhost:8000/docs
3. **Test endpoints**:
   - GET `/` → `{"Hello": "World"}`
   - GET `/items/123?q=test` → `{"item_id": 123, "q": "test"}`
4. **Highlight**: "FastAPI automatically validates types and generates docs!"

### Pydantic Validation Demo (90 seconds)
1. **Start server**: `uvicorn pydantic_data_validation_example:app --reload`
2. **Open docs**: http://localhost:8000/docs
3. **Create user** (POST `/users`):
   ```json
   {
     "name": "John Doe",
     "email": "john@example.com", 
     "age": 30,
     "interests": ["Python", "AI"]
   }
   ```
4. **Show validation** - Try invalid data:
   ```json
   {
     "name": "X",           // Too short!
     "email": "invalid",    // Invalid email!
     "age": 200            // Too old!
   }
   ```
5. **Get users**: GET `/users` 
6. **Update user**: PUT `/users/1`
7. **Highlight**: "Pydantic validates data automatically with clear error messages!"

## 🔥 Key FastAPI Features Demonstrated

### Automatic Data Validation
```python
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr = Field(...)
    age: int = Field(..., ge=13, le=120)
```

### Async Support
```python
@app.post("/users")
async def create_user(user: UserCreate):
    await asyncio.sleep(0.1)  # Simulate DB operation
    return UserResponse(**new_user)
```

### Automatic Documentation
- Interactive docs at `/docs` (Swagger UI)
- Alternative docs at `/redoc` 
- OpenAPI schema at `/openapi.json`

### Type Safety & IDE Support
- Full type hints throughout
- Automatic request/response validation
- IntelliSense support in IDEs

## 🛠 Next Steps

After running these examples, participants will understand:
- How FastAPI leverages Python type hints
- Pydantic's role in data validation
- Async programming in web APIs
- Auto-generated API documentation
- Error handling and HTTP status codes

These concepts will be essential when we integrate **Pydantic-AI agents** and **MCP servers** in the main tutorial!

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Type Hints Guide](https://docs.python.org/3/library/typing.html)

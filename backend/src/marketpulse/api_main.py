"""FastAPI entry point for product CRUD and health checks."""

import os

from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError as ValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from marketpulse.application.products import ProductService
from marketpulse.domain.products import ProductError
from marketpulse.infrastructure.database import make_engine
from marketpulse.infrastructure.products import PostgresProductRepository


engine = make_engine()
service = ProductService(PostgresProductRepository(engine), int(os.getenv("PRICE_STALE_AFTER_SECONDS", "180")))
app = FastAPI(title="MarketPulse API", version="1.0.0")


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    coinbase_product_id: str = Field(min_length=3, max_length=32)
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    coinbase_product_id: str | None = Field(default=None, min_length=3, max_length=32)
    is_active: bool | None = None


@app.exception_handler(ProductError)
async def product_error_handler(_request, exc: ProductError):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": str(exc)}})


@app.exception_handler(ValidationError)
async def validation_error_handler(_request, exc: ValidationError):
    errors = {"error": {"code": "validation_error", "message": "Check the submitted product fields."}}
    return JSONResponse(status_code=422, content=errors)


@app.get("/api/v1/health/live")
def live():
    return {"status": "ok"}


@app.get("/api/v1/health/ready")
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready"}
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "not_ready"})


@app.get("/api/v1/products")
def list_products():
    return service.list_products()


@app.get("/api/v1/products/{product_id}")
def get_product(product_id: int):
    return service.get_product(product_id)


@app.post("/api/v1/products", status_code=201)
def create_product(product: ProductCreate):
    return service.create_product(product.name, product.coinbase_product_id, product.is_active)


@app.patch("/api/v1/products/{product_id}")
def update_product(product_id: int, changes: ProductUpdate):
    values = changes.model_dump(exclude_unset=True)
    if not values:
        return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Provide at least one field to update."}})
    return service.update_product(product_id, values)


@app.delete("/api/v1/products/{product_id}", status_code=204)
def delete_product(product_id: int):
    service.delete_product(product_id)
    return Response(status_code=204)

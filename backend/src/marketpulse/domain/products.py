"""Product rules and repository contract."""

from typing import Protocol
import re


class ProductError(Exception):
    status_code = 400
    code = "product_error"


class InvalidProduct(ProductError):
    status_code = 422
    code = "validation_error"


class DuplicateProduct(ProductError):
    status_code = 409
    code = "product_already_exists"


class ProductNotFound(ProductError):
    status_code = 404
    code = "product_not_found"


class ProductRepository(Protocol):
    def list_products(self) -> list[dict]: ...
    def get_product(self, product_id: int) -> dict | None: ...
    def create_product(self, values: dict) -> dict: ...
    def update_product(self, product_id: int, values: dict) -> dict | None: ...
    def delete_product(self, product_id: int) -> bool: ...


def validate_product(name: str, coinbase_product_id: str) -> dict:
    clean_name = name.strip()
    market_id = coinbase_product_id.strip().upper()
    parts = market_id.split("-")
    if not clean_name or len(clean_name) > 80:
        raise InvalidProduct("Name must contain 1 to 80 characters.")
    if len(market_id) > 32 or not re.fullmatch(r"[A-Z0-9]{1,15}-[A-Z0-9]{1,15}", market_id):
        raise InvalidProduct("Product ID must use BASE-QUOTE format, for example BTC-USD.")
    return {
        "name": clean_name,
        "coinbase_product_id": market_id,
        "base_currency": parts[0],
        "quote_currency": parts[1],
    }

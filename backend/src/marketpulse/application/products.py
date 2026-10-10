"""Product CRUD use cases."""

from datetime import datetime, timezone

from marketpulse.domain.products import InvalidProduct, ProductNotFound, ProductRepository, validate_product


class ProductService:
    def __init__(self, repository: ProductRepository, stale_after_seconds: int = 180):
        self._repository = repository
        self._stale_after_seconds = stale_after_seconds

    def list_products(self) -> list[dict]:
        return [self._present(row) for row in self._repository.list_products()]

    def get_product(self, product_id: int) -> dict:
        row = self._repository.get_product(product_id)
        if row is None:
            raise ProductNotFound("Product was not found.")
        return self._present(row)

    def create_product(self, name: str, market_id: str, is_active: bool = True) -> dict:
        values = validate_product(name, market_id)
        values["is_active"] = is_active
        return self._present(self._repository.create_product(values))

    def update_product(self, product_id: int, changes: dict) -> dict:
        current = self._repository.get_product(product_id)
        if current is None:
            raise ProductNotFound("Product was not found.")
        if any(value is None for value in changes.values()):
            raise InvalidProduct("Product fields cannot be null.")
        name = changes.get("name", current["name"])
        market_id = changes.get("coinbase_product_id", current["coinbase_product_id"])
        values = validate_product(name, market_id)
        values["is_active"] = changes.get("is_active", current["is_active"])
        updated = self._repository.update_product(product_id, values)
        if updated is None:
            raise ProductNotFound("Product was not found.")
        return self._present(updated)

    def delete_product(self, product_id: int) -> None:
        if not self._repository.delete_product(product_id):
            raise ProductNotFound("Product was not found.")

    def _present(self, row: dict) -> dict:
        retrieved = row["retrieved_at"]
        if retrieved is None:
            status = "unavailable" if row["last_attempt_at"] else "not_fetched"
        else:
            if retrieved.tzinfo is None:
                retrieved = retrieved.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - retrieved).total_seconds()
            status = "current" if age <= self._stale_after_seconds else "stale"
        return {
            "id": row["id"],
            "name": row["name"],
            "coinbase_product_id": row["coinbase_product_id"],
            "quote_currency": row["quote_currency"],
            "is_active": row["is_active"],
            "price": str(row["price"]) if row["price"] is not None else None,
            "price_as_of": retrieved,
            "price_status": status,
            "last_attempt_at": row["last_attempt_at"],
            "last_error_category": row["last_error_category"],
        }

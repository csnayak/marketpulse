"""PostgreSQL product repository."""

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine

from marketpulse.domain.products import DuplicateProduct


SELECT_PRODUCTS = text("""SELECT p.id, p.name, p.coinbase_product_id, p.quote_currency, p.is_active,
    q.price, q.retrieved_at, q.last_attempt_at, q.last_error_category
    FROM tracked_products p LEFT JOIN latest_quotes q ON q.product_id = p.id""")


class PostgresProductRepository:
    def __init__(self, engine: Engine):
        self._engine = engine

    def list_products(self) -> list[dict]:
        with self._engine.connect() as connection:
            rows = connection.execute(text(str(SELECT_PRODUCTS) + " ORDER BY lower(p.name), p.id")).mappings()
            return [dict(row) for row in rows]

    def get_product(self, product_id: int) -> dict | None:
        with self._engine.connect() as connection:
            row = connection.execute(
                text(str(SELECT_PRODUCTS) + " WHERE p.id = :id"), {"id": product_id}
            ).mappings().first()
            return dict(row) if row else None

    def create_product(self, values: dict) -> dict:
        try:
            with self._engine.begin() as connection:
                result = connection.execute(text("""INSERT INTO tracked_products
                    (name, coinbase_product_id, base_currency, quote_currency, is_active, source)
                    VALUES (:name, :coinbase_product_id, :base_currency, :quote_currency, :is_active, 'manual')
                    RETURNING id"""), values)
                product_id = result.scalar_one()
        except IntegrityError as exc:
            raise DuplicateProduct("That Coinbase product is already tracked.") from exc
        return self.get_product(product_id)  # type: ignore[return-value]

    def update_product(self, product_id: int, values: dict) -> dict | None:
        try:
            with self._engine.begin() as connection:
                old_market = connection.execute(
                    text("SELECT coinbase_product_id FROM tracked_products WHERE id = :id"), {"id": product_id}
                ).scalar_one_or_none()
                if old_market is None:
                    return None
                if old_market != values["coinbase_product_id"]:
                    connection.execute(text("DELETE FROM latest_quotes WHERE product_id = :id"), {"id": product_id})
                connection.execute(text("""UPDATE tracked_products SET name=:name,
                    coinbase_product_id=:coinbase_product_id, base_currency=:base_currency,
                    quote_currency=:quote_currency, is_active=:is_active, updated_at=now()
                    WHERE id=:id"""), {**values, "id": product_id})
        except IntegrityError as exc:
            raise DuplicateProduct("That Coinbase product is already tracked.") from exc
        return self.get_product(product_id)

    def delete_product(self, product_id: int) -> bool:
        with self._engine.begin() as connection:
            result = connection.execute(text("DELETE FROM tracked_products WHERE id=:id"), {"id": product_id})
            return result.rowcount > 0

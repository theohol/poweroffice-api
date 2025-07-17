import sqlalchemy
from config import DATABASE_URI

engine = sqlalchemy.create_engine(DATABASE_URI)


def get_customers_to_invoice():
    with engine.connect() as connection:
        result = connection.execute(
            sqlalchemy.text(
                "SELECT id, name, poweroffice_customer_code FROM customers WHERE needs_invoicing = TRUE;"
            )
        )
        return result.fetchall()


def get_products_for_customer(customer_id):
    with engine.connect() as connection:
        query = sqlalchemy.text(
            "SELECT product_code, description, quantity, unit_price FROM order_items WHERE customer_id = :cid AND invoiced = FALSE;"
        )
        result = connection.execute(query, {"cid": customer_id})
        return result.fetchall()


def mark_items_as_invoiced(customer_id):
    """Flags items as invoiced to prevent duplicates."""
    with engine.connect() as connection:
        query = sqlalchemy.text(
            "UPDATE order_items SET invoiced = TRUE WHERE customer_id = :cid;"
        )
        connection.execute(query, {"cid": customer_id})
        # You might also update the customer table
        # cust_query = sqlalchemy.text("UPDATE customers SET needs_invoicing = FALSE WHERE id = :cid;")
        # connection.execute(cust_query, {"cid": customer_id})

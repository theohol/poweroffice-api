import database
import poweroffice_api
from datetime import datetime, timezone

def run_invoice_routine():
    """Main function to execute the entire invoicing process."""
    print("Starting invoicing routine...")
    
    customers = database.get_customers_to_invoice()
    if not customers:
        print("No customers to invoice today.")
        return

    print(f"Found {len(customers)} customers to process.")

    for customer in customers:
        customer_id, customer_name, po_customer_code = customer
        print(f"\nProcessing customer: {customer_name} (ID: {customer_id})")
        
        products = database.get_products_for_customer(customer_id)
        if not products:
            print(f"No products to invoice for {customer_name}. Skipping.")
            continue

        # Get the current date in ISO 8601 format (UTC)
        current_date = datetime.now(timezone.utc).isoformat()

        # Transform data into the PowerOffice GO API format
        # This structure is an EXAMPLE. You MUST match the official API documentation.
        order_payload = {
            "customerCode": po_customer_code,
            "orderDate": current_date,
            "deliveryDate": current_date,
            "lines": [
                {
                    "productCode": p.product_code,
                    "description": p.description,
                    "quantity": float(p.quantity), # Ensure correct data types
                    "unitPrice": float(p.unit_price)
                } for p in products
            ]
        }

        print(f"Sending order to PowerOffice for {len(products)} items.")
        result = poweroffice_api.create_order(order_payload)

        if result.get("success"):
            print(f"Successfully created order for {customer_name}.")
            # On success, mark the items as processed in our DB
            database.mark_items_as_invoiced(customer_id)
            print("Marked items as invoiced in local database.")
        else:
            print(f"FAILED to create order for {customer_name}. Error: {result.get('error')}")
            # Decide on error handling: retry later? Send a notification?

    print("\nInvoicing routine finished.")

if __name__ == "__main__":
    run_invoice_routine()


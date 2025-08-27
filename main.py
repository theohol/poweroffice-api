import json
from datetime import datetime
from dotenv import load_dotenv
from db_connector import DatabaseConnector
from poweroffice_api import PowerOfficeAPI

# --- Configuration for Product Code Mapping ---
# Maps the 'nr' from the 'produkter' table to the actual PowerOffice product code.
PRODUCT_CODE_MAP = {
    1: "8",  # 'nr' 1 from db maps to product code "6" in PowerOffice
    2: "3",
    3: "10",
    4: "",  # An empty string will cause this product to be skipped
    5: "8",
}

PRICE_FROM_PO_CODES = {
    "3",
    "10"
}

TRAFFIC_PRODUCT_CODE = "7"  # The PowerOffice product code for "sip trunk traffic"


def map_db_to_sales_order(customer_data):
    order_lines = []
    traffic_info = customer_data.get("traffic_info")

    has_predictive_dialer = False

    # 1. Process standard products from the 'produkter' table
    for product in customer_data.get("products", []):
        db_product_nr = product.get("nr")

        if db_product_nr == 2:
            has_predictive_dialer = True

        poweroffice_code = PRODUCT_CODE_MAP.get(db_product_nr)

        if poweroffice_code:
            line = {
                "productCode": poweroffice_code,
                "description": product.get("description"),
            }

            if db_product_nr == 2 and traffic_info and traffic_info.get("price") is not None:
                line["quantity"] = float(traffic_info.get("quantity", 0))
                print(f"  -> INFO: Using 'faktura' quantity ({line['quantity']}) as quantity for Predictive product.")

            else:
                line["quantity"] = float(product.get("quantity", 0))


            if poweroffice_code not in PRICE_FROM_PO_CODES:
                line["ProductUnitPrice"] = float(product.get("unit_price", 0))

            order_lines.append(line)
        else:
            print(
                f"⚠️ WARNING: No PowerOffice product code mapping found for DB product 'nr' {
                    db_product_nr
                }. Skipping line."
            )

    # 2. If no predictive is found, use nextcom dialer instead
    if not has_predictive_dialer and traffic_info and traffic_info.get("quantity"):
        traffic_quantity = float(traffic_info.get("quantity", 0))

        if traffic_quantity > 0:
            print("  -> INFO: No predictive dialer found. Adding Normal Dialer (code=1) with traffic quantity.")
            order_lines.append({
                "productCode": "1",
                "description": "Nextcom Dialer",
                "quantity": traffic_quantity
            })

    # 3. Process the extra "sip trunk traffic" line from the 'faktura' table
    if traffic_info and traffic_info.get("price") is not None:
        order_lines.append({
            "productCode": TRAFFIC_PRODUCT_CODE,
            "description": "SIP Trunk Traffic",
            "ProductUnitPrice": float(traffic_info.get("price", 0)),
            "quantity": 1,
        })

    if not order_lines: 
        return None


    customer_no = customer_data.get("customer_info", {}).get("organization_no")
    if not customer_no:
        print(
            f"Skipping order for systemid {
                customer_data.get('customer_info', {}).get('systemid')
            } due to missing organization number."
        )
        return None

    sales_order_payload = {
        "customerNo": customer_no,
        "orderDate": datetime.now().strftime("%Y-%m-%d"),
        "SalesOrderLines": order_lines,
    }
    return sales_order_payload


def process_and_create_orders(all_customers_data, po_api):
    if not all_customers_data:
        print("No customer data found to process.")
        return

    for systemid, data in all_customers_data.items():
        print("-" * 50)
        customer_name = data.get("customer_info", {}).get(
            "name", f"Customer {systemid}"
        )
        print(f"Preparing order for {customer_name} (System ID: {systemid})")

        sales_order = map_db_to_sales_order(data)

        if sales_order is None:
            print("No valid lines to invoice for this customer. Skipping.")
            continue

        print("\n--- Sales Order Preview ---")
        print(json.dumps(sales_order, indent=2))
        print("---------------------------\n")

        proceed = input(
            "Do you want to create this sales order via the API? (y/n): "
        ).lower()
        if proceed == "y":
            result = po_api.create_sales_order(sales_order)
            if result:
                print("API Response:", json.dumps(result, indent=2))
        else:
            print("Skipping API creation for this order.")


def main_all_customers():
    print("Starting process for ALL customers...")
    try:
        db = DatabaseConnector()
        po_api = PowerOfficeAPI()
        customers_data = db.get_all_customer_data()
        process_and_create_orders(customers_data, po_api)
        db.close_connection()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    print("\nProcess finished.")


def main_single_customer(system_id):
    print(f"Starting process for SINGLE customer (System ID: {system_id})...")
    try:
        db = DatabaseConnector()
        po_api = PowerOfficeAPI()
        # This method remains for testing, but won't filter faktura by date
        customer_data = db.get_single_customer_data(system_id)
        process_and_create_orders(customer_data, po_api)
        db.close_connection()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    print("\nProcess finished.")


if __name__ == "__main__":
    load_dotenv()

    print("Sales Order Creation Script")
    print("1. Create orders for ALL customers (for current month)")
    print("2. Create an order for a SINGLE customer (for current month)")
    choice = input("Please choose an option (1 or 2): ")

    if choice == "1":
        main_all_customers()
    elif choice == "2":
        try:
            cust_id_input = input("Enter the internal System ID to process: ")
            cust_id = int(cust_id_input)
            main_single_customer(cust_id)
        except ValueError:
            print("Invalid System ID. Please enter a whole number.")
    else:
        print("Invalid choice. Exiting.")

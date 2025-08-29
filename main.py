import json
from datetime import datetime
import mysql.connector
import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env file

# PowerOffice Config
PO_APP_KEY = os.getenv("PO_APP_KEY")
PO_CLIENT_KEY = os.getenv("PO_CLIENT_KEY")
PO_SUB_KEY = os.getenv("PO_SUB_KEY")
#PO_API_BASE_URL = "https://api.poweroffice.net/v2"  # Verify the correct URL


class DatabaseConnector:
    def __init__(self):
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
            )
            self.cursor = self.connection.cursor(dictionary=True)
            print("Successfully connected to the database.")
        except mysql.connector.Error as err:
            print("-" * 60)
            print("FATAL: Could not connect to the database.")
            print(f"Original database error: {err}")
            print("-" * 60)
            raise

    def _fetch_data(self, query, params=None):
        """Helper method to execute a fetch query."""
        if not self.connection or not self.connection.is_connected():
            print("Error: Database connection is not available.")
            return None
        try:
            self.cursor.execute(query, params or ())
            return self.cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Database query failed: {err}")
            return None

    def _process_results(self, results):
        if not results:
            return {}

        customers_data = {}
        for row in results:
            system_id = row.get("systemid")
            if system_id is None:
                continue

            if system_id not in customers_data:
                customers_data[system_id] = {
                    "customer_info": {
                        "systemid": system_id,
                        "organization_no": row.get("organization_no"),
                        "name": f"Customer (Org No: {row.get('organization_no')})",
                    },
                    "products": [],
                    "traffic_info": {},
                    "_added_products": set(),
                }

            product_nr = row.get("product_nr")
            if (
                product_nr is not None
                and product_nr not in customers_data[system_id]["_added_products"]
            ):
                customers_data[system_id]["products"].append(
                    {
                        "nr": product_nr,
                        "description": row.get("product_description"),
                        "quantity": row.get("product_quantity"),
                        "unit_price": row.get("product_price"),
                    }
                )
                customers_data[system_id]["_added_products"].add(product_nr)


            if not customers_data[system_id]["traffic_info"]:
                traffic_price = row.get("traffic_price")
                traffic_quantity = row.get("traffic_quantity")
                if traffic_price is not None or traffic_quantity is not None:
                    customers_data[system_id]["traffic_info"] = {
                        "price": traffic_price,
                        "quantity": traffic_quantity
                    }

        for data in customers_data.values():
            del data["_added_products"]

        return customers_data

    def get_all_customer_data(self):
        now = datetime.now()
        current_month = now.month
        current_year = now.year

        query = """
            SELECT 
                cd.systemid,
                cd.kundenr AS organization_no,
                p.nr AS product_nr,
                p.vare AS product_description,
                p.antall AS product_quantity,
                p.pris AS product_price,
                f.max_traffic_price AS traffic_price,
                f.total_traffic_quantity AS traffic_quantity
            FROM 
                custdata cd
            LEFT JOIN 
                produkter p ON cd.systemid = p.systemid AND p.nr IS NOT NULL
            LEFT JOIN (
                SELECT 
                    systemid, 
                    SUM(belop) AS max_traffic_price,
                    MAX(antall) as total_traffic_quantity
                FROM 
                    faktura
                WHERE 
                    MONTH(dato) = %s AND YEAR(dato) = %s
                GROUP BY 
                    systemid
            ) AS f ON cd.systemid = f.systemid
            WHERE
                cd.kundenr IS NOT NULL AND cd.kundenr != ''
            ORDER BY
                cd.systemid;
        """
        results = self._fetch_data(query, (current_month, current_year))
        return self._process_results(results)

    def get_single_customer_data(self, system_id):

        now = datetime.now()
        current_month = now.month;
        current_year = now.year;

        query = """
            SELECT 
                cd.systemid,
                cd.kundenr AS organization_no,
                p.nr AS product_nr,
                p.vare AS product_description,
                p.antall AS product_quantity,
                p.pris AS product_price,
                f.max_traffic_price AS traffic_price,
                f.total_traffic_quantity AS traffic_quantity
            FROM 
                custdata cd
            LEFT JOIN 
                produkter p ON cd.systemid = p.systemid AND p.nr IS NOT NULL
            LEFT JOIN (
                SELECT
                    systemid,
                    SUM(belop) AS max_traffic_price,
                    MAX(antall) as total_traffic_quantity
                FROM 
                    faktura
                WHERE
                    MONTH(dato) = %s AND YEAR(dato) = %s
                GROUP BY
                    systemid
            ) AS f ON cd.systemid = f.systemid
            WHERE
                cd.kundenr IS NOT NULL AND cd.kundenr != ''
                AND cd.systemid = %s
            ORDER BY
                cd.systemid;
        """

        results = self._fetch_data(query, (current_month, current_year, system_id))
        return self._process_results(results)

    def close_connection(self):
        """Closes the database connection."""
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()
            print("Database connection closed.")


class PowerOfficeAPI:

    TOKEN_URL = "https://goapi.poweroffice.net/oauth/Token"
    API_BASE_URL = "https://goapi.poweroffice.net/v2"

    def __init__(self):
        """
        Initializes the API client with credentials from environment variables.
        """
        self.client_key = PO_CLIENT_KEY
        self.app_key = PO_APP_KEY
        self.subscription_key = PO_SUB_KEY
        self.access_token = None

        if not all([self.client_key, self.app_key, self.subscription_key]):
            raise ValueError(
                "API credentials not found in environment variables.")

    def _get_access_token(self):
        auth_string = f"{self.app_key}:{self.client_key}"
        base64_string = base64.b64encode(
            auth_string.encode("ascii")).decode("ascii")

        # --- API Request ---
        # The payload for the token request
        headers = {
            "Authorization": f"Basic {base64_string}",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        payload = {"grant_type": "client_credentials"}

        try:
            # Make the POST request to the token endpoint
            response = requests.post(
                self.TOKEN_URL, headers=headers, data=payload)

            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()

            # --- Success ---
            # Parse the JSON response
            self.access_token = response.json().get("access_token")

            print("\n✅ --- Success! --- ✅")

        except requests.exceptions.HTTPError as http_err:
            # --- Failure ---
            print(f"\n❌ --- HTTP Error Occurred --- ❌")
            print(f"Status Code: {http_err.response.status_code}")
            print(f"Response Body: {http_err.response.text}")
            self.access_token = None
        except requests.exceptions.RequestException as req_err:
            print(f"\n❌ --- Request Error Occurred --- ❌")
            print(f"Error: {req_err}")
            self.access_token = None

        except Exception as e:
            print(f"\n❌ --- An Unexpected Error Occurred --- ❌")
            print(f"Error: {e}")
            self.access_token = None

    def create_sales_order(self, order_payload):
        if not self.access_token:
            self._get_access_token()
            if not self.access_token:
                print("Cannot create sales order without an access token.")
                return None

        url = f"{self.API_BASE_URL}/SalesOrders/Complete"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
        }

        try:
            print(f"Sending sales order for customer: {order_payload.get('customerNo')}")
            response = requests.post(url, headers=headers, json=order_payload)
            response.raise_for_status()
            print("Sales order created successfully!")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating sales order: {e}")
            print(
                f"Response content: {e.response.text if e.response else 'No response'}")
            return None

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
                f"⚠️ WARNING: No PowerOffice product code mapping found for DB product 'nr' {db_product_nr}. Skipping line."
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
            f"Skipping order for systemid {customer_data.get('customer_info', {}).get('systemid')} due to missing organization number.")
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

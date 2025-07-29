import mysql.connector
import os
from datetime import datetime


class DatabaseConnector:
    """
    Handles connections and complex data fetching from the database by joining
    custdata, produkter, and faktura tables.
    """

    def __init__(self):
        """
        Initializes the database connection using credentials from environment variables.
        """
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
        """Helper function to process the raw SQL results into a structured dictionary."""
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
                    "traffic_info": None,
                }

            if row.get("product_nr") is not None:
                customers_data[system_id]["products"].append(
                    {
                        "nr": row.get("product_nr"),
                        "description": row.get("product_description"),
                        "quantity": row.get("product_quantity"),
                        "unit_price": row.get("product_price"),
                    }
                )

            if (
                row.get("traffic_price") is not None
                and customers_data[system_id]["traffic_info"] is None
            ):
                customers_data[system_id]["traffic_info"] = {
                    "price": row.get("traffic_price")
                }

        return customers_data

    def get_all_customer_data(self):
        """
        Fetches and joins data for all valid customers for the current month.
        - Ignores customers with no organization number.
        - Only includes 'faktura' data if the 'dato' is in the current month.
        - Ignores 'produkter' where 'nr' is NULL.
        """
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
                f.belop AS traffic_price
            FROM 
                custdata cd
            LEFT JOIN 
                produkter p ON cd.systemid = p.systemid AND p.nr IS NOT NULL
            LEFT JOIN 
                faktura f ON cd.systemid = f.systemid AND MONTH(f.dato) = %s AND YEAR(f.dato) = %s
            WHERE
                cd.kundenr IS NOT NULL AND cd.kundenr != ''
            ORDER BY
                cd.systemid;
        """
        results = self._fetch_data(query, (current_month, current_year))
        return self._process_results(results)

    def get_single_customer_data(self, system_id):
        """
        Fetches and joins data for a single customer based on their systemid.
        NOTE: This method does NOT filter the 'faktura' table by date.
        It is intended for testing and fetching all data for one customer.
        """
        query = """
            SELECT 
                cd.systemid,
                cd.kundenr AS organization_no,
                p.nr AS product_nr,
                p.vare AS product_description,
                p.antall AS product_quantity,
                p.pris AS product_price,
                f.belop AS traffic_price
            FROM 
                custdata cd
            LEFT JOIN 
                produkter p ON cd.systemid = p.systemid
            LEFT JOIN 
                faktura f ON cd.systemid = f.systemid
            WHERE
                cd.systemid = %s;
        """
        results = self._fetch_data(query, (system_id,))
        return self._process_results(results)

    def close_connection(self):
        """Closes the database connection."""
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()
            print("Database connection closed.")

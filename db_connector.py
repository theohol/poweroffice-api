import mysql.connector
import os
from datetime import datetime


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

import requests
import base64
from dotenv import load_dotenv
from config import PO_APP_KEY, PO_CLIENT_KEY, PO_SUB_KEY

load_dotenv()


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
            print(
                f"Sending sales order for customer: {
                    order_payload.get('customerNo')}"
            )
            response = requests.post(url, headers=headers, json=order_payload)
            response.raise_for_status()
            print("Sales order created successfully!")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating sales order: {e}")
            print(
                f"Response content: {
                    e.response.text if e.response else 'No response'}"
            )
            return None

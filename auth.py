import os
import requests
import base64
import json
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

# --- Configuration ---
# Retrieve credentials from environment variables
app_key = os.getenv("PO_APP_KEY")
client_key = os.getenv("PO_CLIENT_KEY")
subscription_key = os.getenv("PO_SUB_KEY")

base_url = "https://goapi.poweroffice.net/demo/v2"

# The official PowerOffice GO token endpoint
token_url = "https://goapi.poweroffice.net/demo/oauth/Token"


def get_access_token():
    """
    Fetches the PowerOffice GO access token using credentials from the
    .env file and prints it to the terminal.
    """

    # --- Validation ---
    # Check if the keys were found in the .env file
    if not all([app_key, client_key, subscription_key]):
        print("Error: PO_APP_KEY, PO_CLIENT_KEY or PO_SUB_KEY not found.")
        print("Please ensure they are set correctly in your .env file.")
        return

    auth_string = f"{app_key}:{client_key}"
    base64_string = base64.b64encode(auth_string.encode("ascii")).decode("ascii")

    # --- API Request ---
    # The payload for the token request
    headers = {
        "Authorization": f"Basic {base64_string}",
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    payload = {"grant_type": "client_credentials"}

    try:
        # Make the POST request to the token endpoint
        response = requests.post(token_url, headers=headers, data=payload)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # --- Success ---
        # Parse the JSON response
        access_token = response.json().get("access_token")

        print("\n✅ --- Success! --- ✅")
        return access_token

    except requests.exceptions.HTTPError as http_err:
        # --- Failure ---
        print(f"\n❌ --- HTTP Error Occurred --- ❌")
        print(f"Status Code: {http_err.response.status_code}")
        print(f"Response Body: {http_err.response.text}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"\n❌ --- Request Error Occurred --- ❌")
        print(f"Error: {req_err}")
        return None
    except Exception as e:
        print(f"\n❌ --- An Unexpected Error Occurred --- ❌")
        print(f"Error: {e}")
        return None


def get_sales_orders(token):
    print("\nStep2: Retrieving sales orders")
    if not token:
        print("\nToken not found.")
        return None

    order_url = f"{base_url}/SalesOrders"
    headers = {
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/json",
    }

    print("Trying to retrieve all sales orders...")
    try:
        response = requests.get(order_url, headers=headers)
        response.raise_for_status()
        all_orders = response.json()
        print(f"✅ Success! Found {len(all_orders)} sales orders.")

        if all_orders:
            print("\n--- First Order Sample ---")
            print(all_orders[0])
            print("--------------------------")

        return all_orders
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to retrieve sales order: {e}")
        if e.response:
            print(f"Response Body: {e.response.text}")
        return None


def create_sales_order(token):
    """
    Creates a generic sales order in PowerOffice GO.
    Returns the new order's data on success, or None on failure.
    """
    print("\nStep 3: Creating a new sales order...")
    if not token:
        return None

    order_url = f"{base_url}/SalesOrders/Complete"
    headers = {
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/json",
    }

    # --- !!! IMPORTANT: REPLACE PLACEHOLDER DATA !!! ---
    # You MUST replace the values for 'customerCode' and 'productCode'
    # with actual codes that exist in your PowerOffice account.
    current_date = datetime.now(timezone.utc).isoformat()
    order_payload = {
        "customerCode": "10000",  # <-- REPLACE with a valid customer code
        "orderDate": current_date,
        "deliveryDate": current_date,
        "reference": "Automated Test Order",
        "lines": [
            {
                "productCode": "30",  # <-- REPLACE with a valid product code
                "description": "Generic Product for Automated Order",
                "quantity": 2,
                "unitPrice": 150.75,
            }
        ],
    }

    print(f"Sending order for customer '{order_payload['customerCode']}'...")

    try:
        response = requests.post(
            order_url, data=json.dumps(order_payload), headers=headers
        )
        response.raise_for_status()
        new_order_data = response.json()
        print(
            f"✅ Sales order created successfully. Order ID: {new_order_data.get('id')}"
        )
        return new_order_data
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create sales order: {e}")
        if e.response:
            print(f"Response Body: {e.response.text}")
        return None


def send_order_by_email(token, order_id, email_address):
    """
    Sends an existing sales order to a specified email address.
    """
    print(f"\nStep 3: Sending order {order_id} to {email_address}...")
    if not token or not order_id:
        return

    # This endpoint is based on common API patterns. Please verify with official docs.
    send_url = f"{base_url}/Orders/{order_id}/send"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Payload to specify the recipient and other email details
    email_payload = {
        "sendTo": email_address,
        "subject": "Your Sales Order Confirmation",
        "message": "Please find your sales order attached. Thank you for your business!",
    }

    try:
        response = requests.post(
            send_url, data=json.dumps(email_payload), headers=headers
        )
        response.raise_for_status()
        # A 200 or 204 No Content response usually indicates success
        if 200 <= response.status_code < 300:
            print(f"✅ Order successfully sent to {email_address}.")
        else:
            print(f"⚠️ Order sending finished with status {response.status_code}.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send email: {e}")
        if e.response:
            print(f"Response Body: {e.response.text}")


# --- Main Execution ---
if __name__ == "__main__":
    # Get the token
    bearer_token = get_access_token()

    if bearer_token:
        # Retrieve sales orders
        retrieve = get_sales_orders(bearer_token)
        # Create the order
        new_order = create_sales_order(bearer_token)

        if new_order:
            # Send the order via email
            order_id_to_send = new_order.get("id")
            recipient_email = "theoholmvik@gmail.com"
            send_order_by_email(bearer_token, order_id_to_send, recipient_email)

    print("\nScript finished.")

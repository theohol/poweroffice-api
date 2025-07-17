import requests
import json
from config import PO_APP_KEY, PO_CLIENT_KEY, PO_API_BASE_URL

# A simple cache for the access token
_access_token = None


def get_access_token():
    """
    Authenticates with PowerOffice and returns an access token.
    Note: PowerOffice GO API might use a more complex auth flow.
    This is a simplified example. Please consult their documentation.
    """
    global _access_token
    if _access_token:
        return _access_token

    # This endpoint is hypothetical, check PowerOffice docs
    auth_url = "https://login.poweroffice.net/connect/token"

    payload = {
        "grant_type": "client_credentials",
        "client_id": PO_APP_KEY,
        "client_secret": PO_CLIENT_KEY,
    }

    try:
        response = requests.post(auth_url, data=payload)
        response.raise_for_status()  # Raises an error for bad responses (4xx or 5xx)
        _access_token = response.json().get("access_token")
        return _access_token
    except requests.exceptions.RequestException as e:
        print(f"Error getting access token: {e}")
        return None


def create_order(order_data):
    """Sends a new order to the PowerOffice GO API."""
    token = get_access_token()
    if not token:
        return {"success": False, "error": "Authentication failed."}

    order_url = f"{PO_API_BASE_URL}/Orders"
    headers = {"Authorization": f"Bearer {token}",
               "Content-Type": "application/json"}

    try:
        response = requests.post(
            order_url, data=json.dumps(order_data), headers=headers
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        print(f"Error creating order: {e}")
        print(f"Response body: {
              e.response.text if e.response else 'No response'}")
        return {"success": False, "error": str(e)}

import os
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env file

# PowerOffice Config
PO_APP_KEY = os.getenv("PO_APP_KEY")
PO_CLIENT_KEY = os.getenv("PO_CLIENT_KEY")
PO_SUB_KEY = os.getenv("PO_SUB_KEY")
PO_API_BASE_URL = "https://api.poweroffice.net/v2"  # Verify the correct URL

# Old database config
# DATABASE_URI = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

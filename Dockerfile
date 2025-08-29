# Use the official Python 3.11 image based on Debian Buster for compatibility
FROM python:3.11-buster

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's build cache
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's source code
COPY . .

# Set the command to run your Python script when the container starts
CMD ["python", "main.py"]

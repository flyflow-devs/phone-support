# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory in the container to /api
WORKDIR /app

# Copy the API directory contents into the container at /api
COPY . .

# Install any needed packages specified in api/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define the command to run the app
CMD ["python", "app.py"]
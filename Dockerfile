# Use a lightweight base image
FROM frolvlad/alpine-python3

# Set the working directory to /app
WORKDIR /tetration-alfred

# Copy required configuration files
ADD alfred_configuration.json apic_data.json brokers_list.txt tetration_credentials.json tetration_alfred.py alfred_utils.py requirements.txt /tetration-alfred/

# Optionally define your proxy environment
#ENV http_proxy host:port
#ENV https_proxy host:port

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Run tetration-alfred!
CMD ["python", "/tetration-alfred/tetration_alfred.py"]
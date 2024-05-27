import uasyncio as asyncio
import network
from machine import Pin
from WIFI_CREDENTIALS import SSID, PASS

# Connect to WiFi
def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            pass
    print('Connected to WiFi:', wlan.ifconfig())

# Dictionary to store URL handlers
url_handlers = {}

def parse_query_params(query_string):
    query_params = {}
    if query_string:
        pairs = query_string.split('&')
        for pair in pairs:
            key, value = pair.split('=')
            query_params[key] = value
    return query_params

def route(url):
    def decorator(handler):
        async def wrapper(request_url, reader, writer):
            # Parse query parameters
            query_params = parse_query_params(request_url.split('?', 1)[-1])

            # Call the handler function with query parameters
            response = await handler(**query_params)

            # Write the response
            response = f'HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n{response}\r\n'
            await writer.awrite(response.encode())

            # Close the connection
            await writer.aclose()

        # Register the wrapper function instead of the handler function
        url_handlers[url] = wrapper
        return handler
    return decorator

# Dispatch incoming HTTP requests to the appropriate handler
async def dispatch_request(reader, writer):
    print('Received request from:', writer.get_extra_info('peername'))

    # Read the first line of the request
    line = await reader.readline()
    line = line.decode().strip()
    method, url, version = line.split()

    # Read the entire request
    while True:
        line = await reader.readline()
        line = line.decode().strip()
        if line == '':
            break
        print('Received header:', line)

    # Call the appropriate handler function
    for handler_url, handler in url_handlers.items():
        if url.startswith(handler_url):
            await handler(url, reader, writer)
            return

    # Send a 404 response if no handler is found
    response = b'HTTP/1.0 404 Not Found\r\n\r\n'
    await writer.awrite(response)
    await writer.aclose()

# Start the async REST API server
async def main():
    # Connect to WiFi
    connect_wifi(SSID, PASS)
    
    # Start server
    server = await asyncio.start_server(dispatch_request, '0.0.0.0', 80)

    print('Server listening on IP: 0.0.0.0')
    print('Server listening on port: 80')

    async with server:
        await server.wait_closed()
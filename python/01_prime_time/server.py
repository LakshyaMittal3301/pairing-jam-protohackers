#!/usr/bin/env python3
"""
Simple TCP Echo Server
Listens for client connections and echoes back any data received.
Handles multiple clients concurrently using threading.
"""

import json
import socket
import sys
import threading

HOST = "0.0.0.0"  # Listen on all available interfaces
PORT = 8080  # Port to listen on


def main():
    # Create a TCP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Allow reuse of address to avoid "Address already in use" errors
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to the address and port
        server_socket.bind((HOST, PORT))

        # Start listening for connections (backlog of 128)
        server_socket.listen(128)
        print(f"TCP Server listening on {HOST}:{PORT}")

        try:
            while True:
                # Accept a client connection
                client_socket, client_address = server_socket.accept()
                print(f"Connection from {client_address}")

                # Handle the client in a separate thread for concurrent serving
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client_socket, client_address),
                    daemon=True,
                )
                client_thread.start()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            sys.exit(0)


def handle_client(client_socket, client_address):
    """Handle a single client connection."""
    try:
        with client_socket:
            while True:
                # Receive data from the client (up to 4096 bytes)
                data = client_socket.recv(4096)

                # If no data received, client has closed the connection
                if not data:
                    print(f"Client {client_address} disconnected")
                    break

                print(
                    f"Received from {client_address}: {data[:100]}"
                )  # Print first 100 bytes

                # Echo the data back to the client
                json_object = json.loads(data.decode("utf-8"))
                print(json_object)
                print(json_object["method"], json_object["number"])
    # client_socket.sendall(data)
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")


if __name__ == "__main__":
    main()

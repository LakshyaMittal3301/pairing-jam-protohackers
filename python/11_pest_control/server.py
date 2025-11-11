#!/usr/bin/env python3
"""
Simple TCP Echo Server
Listens for client connections and echoes back any data received.
Handles multiple clients concurrently using threading.
"""

import socket
import sys
import threading

from client import AuthorityServerClient
from messages import *

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


def process_message(message: bytes, client_socket, state):
    # 1. check that the checksum is valid
    # if checksum is invalid, then send back error

    checksum_total = 0
    for val in message:
        checksum_total += val
    if checksum_total % 256 != 0:
        client_socket.sendall(error_message("Checksum failed"))
        return

    # 2. parse the message type

    if message[0] == b"\x50":
        # process hello
        res = parse_hello_message(message)
        if res["protocol"] != "pestcontrol" or res["version"] != 1:
            client_socket.sendall(error_message("Invalid hello"))
            return
        client_socket.sendall(hello_message("pestcontrol", 1))

        state["hello"] = True
        return

    if state["hello"] == False:
        client_socket.sendall(error_message("Missing hello as first message"))
        return

    if message[0] == b"\x58":
        res = parse_site_visit_message(message)

        populations = res["populations"]
        species_count = {}
        bad = False
        for entry in populations:
            if entry["species"] not in species_count:
                species_count[entry["species"]] = entry["count"]
            elif species_count[entry["species"]] == entry["count"]:
                pass
            else:
                bad = True
        if bad:
            client_socket.sendall(
                error_message("Multiple conflicting counts for the same species")
            )
            return


def handle_client(client_socket, client_address):
    """Handle a single client connection."""
    data_buffer = b""
    state = {"hello": False}
    try:
        with client_socket:
            while True:
                # Receive data from the client (up to 4096 bytes)
                data = client_socket.recv(4096)

                # If no data received, client has closed the connection
                if not data:
                    print(f"Client {client_address} disconnected")
                    break

                print(f"Received from {client_address}: {data}")

                data_buffer += data

                if len(data_buffer) < 5:
                    continue

                # process all messages in data_buffer
                while True:
                    message_len = parse_u32(data_buffer, 1)
                    if len(data_buffer) < message_len:
                        break
                    current_message = data_buffer[:message_len]
                    data_buffer = data_buffer[message_len:]

                    process_message(current_message, client_socket, state)
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")


if __name__ == "__main__":
    main()

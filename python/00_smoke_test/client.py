#!/usr/bin/env python3
"""
Simple TCP Client for the Echo Server
Connects to the echo server and sends/receives data programmatically.
"""

import socket

HOST = 'localhost'  # Server hostname or IP address
PORT = 8080         # Server port


class EchoClient:
    """A simple TCP client for the echo server."""

    def __init__(self, host=HOST, port=PORT):
        """Initialize the client with host and port."""
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        """Connect to the server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        print(f"Connected to {self.host}:{self.port}")

    def send(self, data):
        """Send data to the server.

        Args:
            data: String or bytes to send
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.socket.sendall(data)
        print(f"Sent: {data}")

    def receive(self, buffer_size=4096):
        """Receive data from the server.

        Args:
            buffer_size: Maximum number of bytes to receive

        Returns:
            Received data as bytes
        """
        data = self.socket.recv(buffer_size)
        print(f"Received: {data}")
        return data

    def send_and_receive(self, data, buffer_size=4096):
        """Send data and receive the echo response.

        Args:
            data: String or bytes to send
            buffer_size: Maximum number of bytes to receive

        Returns:
            Received data as bytes
        """
        self.send(data)
        return self.receive(buffer_size)

    def close(self):
        """Close the connection."""
        if self.socket:
            self.socket.close()
            print("Connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """Example usage of the EchoClient."""
    # Using context manager for automatic connection handling
    with EchoClient() as client:
        # Send and receive some test messages
        response = client.send_and_receive("Hello, server!")
        assert response == b"Hello, server!"

        response = client.send_and_receive("Testing echo...")
        assert response == b"Testing echo..."

        # Send binary data
        binary_data = b'\x00\x01\x02\x03\x04'
        response = client.send_and_receive(binary_data)
        assert response == binary_data

        print("\nAll tests passed!")


if __name__ == "__main__":
    main()

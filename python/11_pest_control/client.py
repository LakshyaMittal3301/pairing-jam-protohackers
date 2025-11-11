import socket

HOST = "pestcontrol.protohackers.com"  # Server hostname or IP address
PORT = 20547  # Server port


class AuthorityServerClient:
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
            data = data.encode("utf-8")
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

    def close(self):
        """Close the connection."""
        if self.socket:
            self.socket.close()
            print("Connection closed")

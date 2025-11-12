import socket

from messages import parse_u32

HOST = "pestcontrol.protohackers.com"  # Server hostname or IP address
PORT = 20547  # Server port


class AuthorityServerClient:
    """A simple TCP client for the echo server."""

    def __init__(self, host=HOST, port=PORT):
        """Initialize the client with host and port."""
        self.host = host
        self.port = port
        self.socket = None
        self.data_buffer = b""

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

    def receive(self):
        """Receive data from the server.

        Args:
            buffer_size: Maximum number of bytes to receive

        Returns:
            Received data as bytes
        """
        while True:
            if len(self.data_buffer) < 5:
                data = self.socket.recv(4096)
                self.data_buffer += data
                print(f"Received: {data}")
                continue

            message_len = parse_u32(self.data_buffer, 1)

            if len(self.data_buffer) < message_len:
                data = self.socket.recv(4096)
                self.data_buffer += data
                print(f"Received: {data}")
                continue

            message = self.data_buffer[:message_len]
            self.data_buffer = self.data_buffer[message_len:]
            return message

    def close(self):
        """Close the connection."""
        if self.socket:
            self.socket.close()
            print("Connection closed")

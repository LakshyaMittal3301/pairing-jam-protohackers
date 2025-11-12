#!/usr/bin/env python3
"""
Simple TCP Echo Server
Listens for client connections and echoes back any data received.
Handles multiple clients concurrently using asyncio.
"""

import asyncio
import sys

from client import AuthorityServerClient
from messages import *

HOST = "0.0.0.0"  # Listen on all available interfaces
PORT = 8080  # Port to listen on


async def main():
    # Create async TCP server
    server = await asyncio.start_server(
        handle_client,
        HOST,
        PORT,
    )

    addr = server.sockets[0].getsockname()
    print(f"TCP Server listening on {addr[0]}:{addr[1]}")

    async with server:
        try:
            await server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            sys.exit(0)


def process_message(message: bytes, writer, state):
    # 1. check that the checksum is valid
    # if checksum is invalid, then send back error

    checksum_total = 0
    for val in message:
        checksum_total += val
    if checksum_total % 256 != 0:
        writer.write(error_message("Checksum failed"))
        return

    # 2. parse the message type

    if message[0] == b"\x50":
        # process hello
        res = parse_hello_message(message)
        if res["protocol"] != "pestcontrol" or res["version"] != 1:
            writer.write(error_message("Invalid hello"))
            return
        writer.write(hello_message("pestcontrol", 1))

        state["hello"] = True
        return

    if state["hello"] == False:
        writer.write(error_message("Missing hello as first message"))
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
            writer.write(
                error_message("Multiple conflicting counts for the same species")
            )
            return


async def handle_client(reader, writer):
    """Handle a single client connection."""
    client_address = writer.get_extra_info('peername')
    print(f"Connection from {client_address}")

    data_buffer = b""
    state = {"hello": False}
    try:
        while True:
            # Receive data from the client (up to 4096 bytes)
            data = await reader.read(4096)

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

                # Process message atomically (no await inside)
                process_message(current_message, writer, state)

            # Drain the writer after processing all messages
            await writer.drain()
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())

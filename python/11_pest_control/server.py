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

all_policies: dict[
    int, dict[str, tuple[int, str]]
] = {}  # maps from site id to another dictionary of species to (policy id, cull/conserve)


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


def validate_checksum(message: bytes) -> bool:
    checksum_total = 0
    for val in message:
        checksum_total += val
    return checksum_total % 256 == 0


def process_message(message: bytes, writer, state):
    # 1. check that the checksum is valid
    # if checksum is invalid, then send back error

    if not validate_checksum(message):
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

        site = res["site"]
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

        # 1. create a new AuthorityServerClient client
        authority_server_client = AuthorityServerClient()
        authority_server_client.connect()

        # 2. send Hello and receive Hello
        # TODO: remember to handle exceptions properly by sending the error message on exception
        authority_server_client.send(hello_message("pestcontrol", 1))
        hello_message = authority_server_client.receive()
        if not validate_checksum(hello_message):
            authority_server_client.send(
                error_message("Bad checksum for authority server hello")
            )
            return
        authority_server_res = parse_hello_message(hello_message)
        if (
            authority_server_res["protocol"] != "pestcontrol"
            or authority_server_res["version"] != 1
        ):
            authority_server_client.send(error_message("Invalid hello"))
            return

        # 3. send DialAuthority and receive TargetPopulations
        authority_server_client.send(dial_authority_message(site))
        target_populations_message = authority_server_client.receive()
        if not validate_checksum(target_populations_message):
            authority_server_client.send(
                error_message("Bad checksum for authority server target populations")
            )
            return
        authority_server_res = parse_target_populations_message(
            target_populations_message
        )
        target_populations = authority_server_res["populations"]

        # 4. iterate over populations and update policies
        for target_population in target_populations:
            species = target_population["species"]
            min_count = target_population["min"]
            max_count = target_population["max"]

            cur_count = populations.get(species, 0)
            if cur_count < min_count:
                # delete policy if there's an existing policy and it's cull
                if (
                    species in all_policies[site]
                    and all_policies[site][species][1] == "cull"
                ):
                    # remove policy
                    authority_server_client.send(
                        delete_policy_message(all_policies[site][species][0])
                    )
                    ok_message = authority_server_client.receive()
                    if not validate_checksum(ok_message):
                        authority_server_client.send(
                            error_message("Bad checksum for authority server ok")
                        )
                        return
                    del all_policies[site][species]

                # add policy if there's no existing conserve policy
                if species not in all_policies[site]:
                    # add policy
                    authority_server_client.send(
                        create_policy_message(species, b"\xa0")
                    )
                    policy_result_message = authority_server_client.receive()
                    if not validate_checksum(policy_result_message):
                        authority_server_client.send(error_message("Bad checksum"))
                        return
                    policy_id = parse_policy_result_message(policy_result_message)[
                        "policy"
                    ]

                    all_policies[site][species] = (policy_id, "conserve")
            elif cur_count > max_count:
                # delete policy if there's an existing policy and it's conserve
                if (
                    species in all_policies[site]
                    and all_policies[site][species][1] == "conserve"
                ):
                    # remove policy
                    authority_server_client.send(
                        delete_policy_message(all_policies[site][species][0])
                    )
                    ok_message = authority_server_client.receive()
                    if not validate_checksum(ok_message):
                        authority_server_client.send(
                            error_message("Bad checksum for authority server ok")
                        )
                        return
                    del all_policies[site][species]

                # add policy if there's no existing cull policy
                if species not in all_policies[site]:
                    # add policy
                    authority_server_client.send(
                        create_policy_message(species, b"\x90")
                    )
                    policy_result_message = authority_server_client.receive()
                    if not validate_checksum(policy_result_message):
                        authority_server_client.send(error_message("Bad checksum"))
                        return
                    policy_id = parse_policy_result_message(policy_result_message)[
                        "policy"
                    ]

                    all_policies[site][species] = (policy_id, "cull")
            else:
                if species in all_policies[site]:
                    # remove policy
                    authority_server_client.send(
                        delete_policy_message(all_policies[site][species][0])
                    )
                    ok_message = authority_server_client.receive()
                    if not validate_checksum(ok_message):
                        authority_server_client.send(
                            error_message("Bad checksum for authority server ok")
                        )
                        return
                    del all_policies[site][species]

        authority_server_client.close()


async def handle_client(reader, writer):
    """Handle a single client connection."""
    client_address = writer.get_extra_info("peername")
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

            print(f"Received from {client_address}: {data.hex(' ')}")

            data_buffer += data

            # process all messages in data_buffer
            while True:
                if len(data_buffer) < 5:
                    break
                message_len = parse_u32(data_buffer, 1)
                if len(data_buffer) < message_len:
                    break
                current_message = data_buffer[:message_len]
                data_buffer = data_buffer[message_len:]

                # Process message atomically (no await inside)
                process_message(current_message, writer, state)

            # Drain the writer after processing all messages
            await writer.drain()
    except asyncio.CancelledError:
        # Task cancellations are expected during shutdown; surface them explicitly for debugging
        print(f"Connection task for {client_address} cancelled")
        raise
    except Exception as e:
        print(f"Error handling client {client_address}: {type(e).__name__}: {e!r}")
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())

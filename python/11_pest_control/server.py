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
    print(f"process_message: len={len(message)} type={message[:1].hex()} state={state}")
    # 1. check that the checksum is valid
    # if checksum is invalid, then send back error

    try:
        if not state["server_hello"]:
            writer.write(hello_message("pestcontrol", 1))
            state["server_hello"] = True

        if not validate_checksum(message):
            print("process_message: checksum invalid")
            writer.write(error_message("Checksum failed"))
            return

        # 2. parse the message type

        if message[:1] == b"\x50":
            # process hello
            res = parse_hello_message(message)
            print(f"process_message: hello parsed {res}")
            if res["protocol"] != "pestcontrol" or res["version"] != 1:
                print("process_message: hello protocol/version mismatch")
                writer.write(error_message("Invalid hello"))
                return
            state["client_hello"] = True
            return

        if not state["client_hello"]:
            print("process_message: received non-hello before hello")
            writer.write(error_message("Missing hello as first message"))
            return

        if message[:1] == b"\x58":
            res = parse_site_visit_message(message)
            print(f"process_message: site visit parsed {res}")

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

            if site not in all_policies:
                all_policies[site] = {}

            # 1. create a new AuthorityServerClient client
            print(f"process_message: connecting to authority for site {site}")
            authority_server_client = AuthorityServerClient()
            authority_server_client.connect()

            try:
                # 2. send Hello and receive Hello
                # TODO: remember to handle exceptions properly by sending the error message on exception
                authority_server_client.send(hello_message("pestcontrol", 1))
                authority_hello_message = authority_server_client.receive()
                print(
                    "process_message: authority hello "
                    f"type={authority_hello_message[:1].hex()} len={len(authority_hello_message)}"
                )
                if not validate_checksum(authority_hello_message):
                    authority_server_client.send(
                        error_message("Bad checksum for authority server hello")
                    )
                    return
                authority_server_res = parse_hello_message(authority_hello_message)
                if (
                    authority_server_res["protocol"] != "pestcontrol"
                    or authority_server_res["version"] != 1
                ):
                    authority_server_client.send(error_message("Invalid hello"))
                    return

                # 3. send DialAuthority and receive TargetPopulations
                authority_server_client.send(dial_authority_message(site))
                target_populations_message = authority_server_client.receive()
                print(
                    "process_message: authority target populations "
                    f"type={target_populations_message[:1].hex()} len={len(target_populations_message)}"
                )
                if not validate_checksum(target_populations_message):
                    authority_server_client.send(
                        error_message(
                            "Bad checksum for authority server target populations"
                        )
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

                    cur_count = species_count.get(species, 0)
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
                                    error_message(
                                        "Bad checksum for authority server ok"
                                    )
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
                                authority_server_client.send(
                                    error_message("Bad checksum")
                                )
                                return
                            policy_id = parse_policy_result_message(
                                policy_result_message
                            )["policy"]

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
                                    error_message(
                                        "Bad checksum for authority server ok"
                                    )
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
                                authority_server_client.send(
                                    error_message("Bad checksum")
                                )
                                return
                            policy_id = parse_policy_result_message(
                                policy_result_message
                            )["policy"]

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
                                    error_message(
                                        "Bad checksum for authority server ok"
                                    )
                                )
                                return
                            del all_policies[site][species]
            except Exception as e:
                authority_server_client.send(error_message("Exception occurred"))

            authority_server_client.close()
    except Exception as e:
        writer.write(error_message("Exception occurred"))


async def handle_client(reader, writer):
    """Handle a single client connection."""
    client_address = writer.get_extra_info("peername")
    print(f"Connection from {client_address}")

    data_buffer = b""
    # state is a client specific
    state = {"client_hello": False, "server_hello": False}
    try:
        while True:
            # Receive data from the client (up to 4096 bytes)
            print(f"reading data for {client_address} ...")
            data = await reader.read(4096)
            print(f"finished reading data for {client_address}")

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
                if message_len > 1000000:
                    if not state["server_hello"]:
                        writer.write(hello_message("pestcontrol", 1))
                        state["server_hello"] = True
                        await writer.drain()
                    writer.write(error_message("Message too long"))
                    await writer.drain()
                    assert False
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
        print(f"Closing writer for {client_address}...")
        writer.close()
        await writer.wait_closed()
        print(f"Writer closed for {client_address}")


if __name__ == "__main__":
    asyncio.run(main())

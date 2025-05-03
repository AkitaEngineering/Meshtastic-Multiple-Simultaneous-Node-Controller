#!/usr/bin/env python3
"""
Meshtastic Multiple Simultaneous Node Controller Demo

This script simulates two separate "tasks" (like MeshSense and an EAS Alerter)
concurrently connecting to the *same* Meshtastic node.

It relies on `ser2net` forwarding the node's USB serial connection to a local TCP port.

See README.md for prerequisites and setup instructions.
"""

import meshtastic
import meshtastic.tcp_interface
import time
import threading
import sys
import random
import logging

# --- Configuration ---
# Hostname or IP address where ser2net is running (usually localhost)
HOSTNAME = "localhost"
# TCP port configured in ser2net (must match ser2net config)
TCP_PORT = 4403
# Interval for simulated tasks (in seconds)
INFO_FETCH_INTERVAL = 60 # How often the "MeshSense" task runs
MESSAGE_SEND_INTERVAL = 120 # How often the "EAS Alerter" task runs

# Enable basic logging for the meshtastic library
# logging.basicConfig(level=logging.DEBUG) # Uncomment for detailed library logs
# ---------------------

# Shared event to signal threads to stop gracefully
stop_event = threading.Event()

def connect_to_node(task_name):
    """
    Attempts to establish a connection to the Meshtastic node via the TCP
    port forwarded by ser2net.

    Args:
        task_name (str): The name of the calling task for logging.

    Returns:
        meshtastic.tcp_interface.TCPInterface or None: The interface object
        if connection is successful, otherwise None.
    """
    print(f"[{task_name}] Attempting to connect to node via TCP at {HOSTNAME}:{TCP_PORT}...")
    try:
        # Each task creates its own independent connection object.
        # The underlying library and ser2net handle multiplexing over the serial port.
        interface = meshtastic.tcp_interface.TCPInterface(
            hostname=HOSTNAME,
            port=TCP_PORT,
            noProto=False, # Default. Set to True only if experiencing connection issues
                           # that might indicate missing protobuf framing over TCP.
            connectNow=True # Try connecting immediately
        )
        # Note: The TCPInterface constructor might return before the connection
        # is fully established in the background thread. We add a small wait.
        time.sleep(3) # Allow time for background connection attempt & initial packets

        # A simple check to see if the connection seems alive
        # Note: localNode might not be populated immediately.
        if interface.is_connected:
             print(f"[{task_name}] Connection successful!")
             return interface
        else:
             print(f"[{task_name}] Connection attempt failed or timed out.")
             interface.close() # Clean up the failed interface
             return None

    except meshtastic.MeshtasticError as e:
        print(f"[{task_name}] MeshtasticError connecting via TCP: {e}")
        print(f"[{task_name}] Check: Is ser2net running? Is config correct (port {TCP_PORT}, device, baud)? Is node connected & powered?")
        return None
    except ConnectionRefusedError:
        print(f"[{task_name}] Connection refused. Is ser2net running and listening on {HOSTNAME}:{TCP_PORT}?")
        return None
    except Exception as e:
        print(f"[{task_name}] Unexpected error during connection: {type(e).__name__}: {e}")
        return None

def simulated_meshsense_task(fetch_interval):
    """
    Simulates a task that periodically fetches node information,
    similar to what MeshSense might do.

    Args:
        fetch_interval (int): How often to fetch info, in seconds.
    """
    task_name = "SimMeshSense"
    interface = None # Initialize interface to None

    try:
        interface = connect_to_node(task_name)
        if not interface:
            print(f"[{task_name}] Could not connect, exiting task.")
            return # Exit thread if connection failed

        while not stop_event.is_set():
            print(f"[{task_name}] Fetching node info...")
            try:
                # Access basic node info. This relies on the interface's
                # background thread receiving and processing packets.
                # Give it a moment after connection before expecting full data.
                if interface.localNode and interface.localNode.user:
                    print(f"  [{task_name}] Local Node: {interface.localNode.user.id} ('{interface.localNode.user.shortName}'), HW: {interface.localNode.hwModel}, FW: {interface.localNode.firmwareVersion}")
                    # Example: List known nodes (might take time to populate)
                    node_count = len(interface.nodes)
                    print(f"  [{task_name}] Known Nodes in Mesh: {node_count}")
                    # for node_id, node_info in interface.nodes.items():
                    #     if node_info.get('user'):
                    #         print(f"    - {node_info['user']['id']} ({node_info['user']['shortName']})")

                elif interface.is_connected:
                     print(f"  [{task_name}] Connected, but local node info not fully populated yet.")
                else:
                     print(f"  [{task_name}] Connection lost.")
                     # Optional: Implement reconnection logic here
                     break # Exit loop if connection lost

            except meshtastic.MeshtasticError as e:
                 print(f"  [{task_name}] Error interacting with node: {e}")
                 # Consider if this error means connection is lost
            except Exception as e:
                 print(f"  [{task_name}] Unexpected error during info fetch: {type(e).__name__}: {e}")

            # Wait for the next interval or until stop event is set
            stop_event.wait(fetch_interval)

    except Exception as e:
        # Catch errors that might occur outside the inner try/except
        print(f"[{task_name}] An unexpected error occurred in the task's main loop: {type(e).__name__}: {e}")
    finally:
        # Ensure the connection is closed when the thread exits
        if interface and interface.is_connected:
            print(f"[{task_name}] Closing connection...")
            interface.close()
            print(f"[{task_name}] Connection closed.")
        elif interface: # If interface exists but wasn't connected or lost connection
            interface.close() # Still attempt cleanup
            print(f"[{task_name}] Interface closed (was not connected).")
        print(f"[{task_name}] Task finished.")


def simulated_eas_alerter_task(send_interval):
    """
    Simulates a task that periodically sends a broadcast message,
    similar to what an EAS Alerter might do.

    Args:
        send_interval (int): How often to send a message, in seconds.
    """
    task_name = "SimEASAlert"
    interface = None # Initialize interface to None

    try:
        interface = connect_to_node(task_name)
        if not interface:
            print(f"[{task_name}] Could not connect, exiting task.")
            return # Exit thread if connection failed

        while not stop_event.is_set():
            # In a real EAS alerter, this would be triggered by an external event (SDR detection)
            # Here, we just send periodically for demonstration.
            message = f"Simulated Alert {random.randint(1000, 9999)} - Check Weather!"
            print(f"[{task_name}] Sending broadcast message: '{message}'")
            try:
                # Send a broadcast text message to the primary channel
                # A real EAS Alerter might send to a specific channel:
                # interface.sendText(message, channelIndex=N)
                # Or send structured data using interface.sendData(...)
                interface.sendText(message)
                print(f"  [{task_name}] Message sent successfully.")

            except meshtastic.MeshtasticError as e:
                 print(f"  [{task_name}] Error sending message: {e}")
                 # Check if the connection is still alive
                 if not interface.is_connected:
                     print(f"  [{task_name}] Connection lost. Exiting send loop.")
                     break # Exit loop if connection lost
            except Exception as e:
                 print(f"  [{task_name}] Unexpected error during send: {type(e).__name__}: {e}")

            # Wait for the next interval or until stop event is set
            stop_event.wait(send_interval)

    except Exception as e:
        # Catch errors that might occur outside the inner try/except
        print(f"[{task_name}] An unexpected error occurred in the task's main loop: {type(e).__name__}: {e}")
    finally:
        # Ensure the connection is closed when the thread exits
        if interface and interface.is_connected:
            print(f"[{task_name}] Closing connection...")
            interface.close()
            print(f"[{task_name}] Connection closed.")
        elif interface: # If interface exists but wasn't connected or lost connection
            interface.close() # Still attempt cleanup
            print(f"[{task_name}] Interface closed (was not connected).")
        print(f"[{task_name}] Task finished.")


def main():
    """Starts the simulated concurrent tasks."""
    print("--- Meshtastic Multi-Client Controller Demo ---")
    print(f"Attempting to connect tasks to node via ser2net at {HOSTNAME}:{TCP_PORT}")
    print(f"Ensure ser2net is configured correctly and running.")
    print("See README.md for full setup instructions.")
    print("-" * 40)

    # Create thread objects for each simulated task
    # Pass the interval arguments to the target functions
    meshsense_thread = threading.Thread(
        target=simulated_meshsense_task,
        args=(INFO_FETCH_INTERVAL,),
        daemon=True # Allows main program to exit even if threads are running
    )
    eas_alerter_thread = threading.Thread(
        target=simulated_eas_alerter_task,
        args=(MESSAGE_SEND_INTERVAL,),
        daemon=True
    )

    threads = [meshsense_thread, eas_alerter_thread]

    try:
        # Start the threads
        for thread in threads:
            thread.start()
            time.sleep(1) # Stagger thread starts slightly

        print("\nSimulated tasks started in background threads.")
        print("Monitoring threads. Press Ctrl+C to stop.")
        print("-" * 40)

        # Keep the main thread alive while the background threads run,
        # checking periodically if they are still active.
        while any(t.is_alive() for t in threads):
            # This loop prevents the main script from exiting immediately.
            # The stop_event is used for graceful shutdown on Ctrl+C.
            time.sleep(1)

        print("-" * 40)
        print("All tasks seem to have finished.")


    except KeyboardInterrupt:
        print("\n" + "-" * 40)
        print("Ctrl+C received. Signaling tasks to stop gracefully...")
        stop_event.set() # Signal all threads to stop their loops
    except Exception as e:
        print(f"\nAn unexpected error occurred in the main execution: {type(e).__name__}: {e}")
        stop_event.set() # Signal threads to stop in case of error
    finally:
        # Wait for threads to finish their current loop and clean up
        print("Waiting for tasks to shut down (up to 5 seconds)...")
        for thread in threads:
            thread.join(timeout=5) # Wait max 5 seconds per thread
            if thread.is_alive():
                print(f"Warning: Thread {thread.name} did not exit cleanly.")

        print("-" * 40)
        print("--- Demo finished ---")
        sys.exit(0) # Explicitly exit with success code

if __name__ == "__main__":
    main()

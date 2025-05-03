# Meshtastic Multiple Simultaneous Node Controller Demo

This project demonstrates a method for allowing multiple applications running on the same machine (e.g., a Raspberry Pi) to control and interact with a single Meshtastic node simultaneously.

## How it Works

1.  **Physical Connection:** A Meshtastic node is connected via USB to the host machine.
2.  **Serial-to-TCP Forwarding:** The `ser2net` utility is configured to listen on a local TCP port (e.g., `4403`) and forward all traffic to and from the Meshtastic node's serial port (e.g., `/dev/ttyUSB0`).
3.  **Application Connection:** Multiple applications (simulated in `multi_controller_demo.py`) use the `meshtastic-python` library to connect to the node via the TCP socket (`localhost:4403`) provided by `ser2net`, instead of directly accessing the serial port.

This allows `ser2net` to manage the single serial connection while providing a network endpoint that multiple clients can connect to.

## Prerequisites

1.  **Meshtastic Node:** A Meshtastic compatible device (e.g., Heltec V3, RAK Wireless).
2.  **Host Machine:** A computer capable of running Python and `ser2net` (e.g., Raspberry Pi, Linux PC).
3.  **Python 3:** Ensure Python 3 is installed.
4.  **`ser2net`:** Install `ser2net` (`sudo apt update && sudo apt install ser2net` on Debian/Ubuntu based systems).
5.  **`meshtastic-python` library:** Install using pip (see Setup).

## Setup

1.  **Connect Node:** Connect your Meshtastic node to the host machine via USB. Identify its serial port (e.g., `/dev/ttyUSB0` or `/dev/ttyACM0`) and note its serial baud rate (check device specs or Meshtastic settings, common values are 115200, 921600).
2.  **Configure `ser2net`:**
    * Edit the `ser2net` configuration file. This is often `/etc/ser2net.conf` (older format) or `/etc/ser2net.yaml` (newer format). Check which one exists on your system.
    * Add a line/section to forward the node's serial port to a TCP port (default in the script is `4403`).
    * **Example for `/etc/ser2net.conf`:**
        ```
        # FORMAT: <TCP PORT>:<STATE>:<TIMEOUT>:<DEVICE>:<OPTIONS>
        4403:raw:0:/dev/ttyUSB0:115200 8DATABITS NONE 1STOPBIT banner
        ```
        *(**Important:** Replace `/dev/ttyUSB0` with your node's actual serial port and `115200` with its correct baud rate)*
    * **Example for `/etc/ser2net.yaml`:**
        ```yaml
        connection: &meshtastic_forward
          accepter: tcp,4403             # Listen on TCP port 4403
          enable: on
          connector: serialdev,          # Connect to a serial device
            /dev/ttyUSB0,               # The serial device path <- CHANGE THIS
            115200n81                   # Serial settings: 115200 baud, no parity, 8 data bits, 1 stop bit <- CHANGE BAUDRATE IF NEEDED
                                        # Common alternatives: 921600n81, 460800n81
        ```
       *(**Important:** Replace `/dev/ttyUSB0` and `115200n81` as needed)*
    * Save the configuration file.
3.  **Restart and Enable `ser2net`:**
    ```bash
    sudo systemctl restart ser2net
    sudo systemctl enable ser2net  # Optional: Make it start on boot
    sudo systemctl status ser2net # Verify it's running without errors
    ```
4.  **Clone/Download Project:** Get the project files (`multi_controller_demo.py`, `requirements.txt`, `README.md`) onto your host machine. Place them in a dedicated directory.
5.  **Install Dependencies:** Navigate to the project directory in your terminal and run:
    ```bash
    pip install -r requirements.txt
    ```
    *(It's recommended to use a Python virtual environment)*

## Running the Demo

Navigate to the project directory in your terminal and run the main script:

```bash
python multi_controller_demo.py
```

You should see output from both the "SimMeshSense" and "SimEASAlert" tasks, indicating they are connecting and interacting with the node concurrently via TCP. Press `Ctrl+C` to stop.

## Troubleshooting

* **Connection Refused:** `ser2net` is likely not running or not listening on the expected port (`4403` by default). Check `sudo systemctl status ser2net` and the configuration file.
* **Connection Timeout / No Data:** `ser2net` might be running, but the serial configuration (port `/dev/ttyUSBx`, baud rate) might be wrong, or the node might not be responding. Double-check the `ser2net` config and ensure the node is powered and connected. Try toggling `noProto=True` in the `TCPInterface` call within the Python script as a test.
* **Permission Denied (Serial Port):** The user running `ser2net` might not have permission to access the serial port. Add the user to the relevant group (often `dialout`): `sudo usermod -a -G dialout $USER` (log out and back in after).
* **MeshtasticError:** Check the specific error message. It might indicate issues with the node itself or the communication protocol.

## Adapting for Real Applications

To use this method with actual applications like MeshSense or the Meshtastic EAS Alerter:

1.  Complete the `ser2net` setup as described above.
2.  Configure *each* application to connect to the Meshtastic node using its **TCP connection option**, pointing it to `localhost` (or `127.0.0.1`) and the TCP port you configured in `ser2net` (e.g., `4403`). Look for command-line arguments like `--host localhost --port 4`

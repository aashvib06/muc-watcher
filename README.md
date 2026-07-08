# RoboLink / UC Watcher

A lightweight network debugging and telemetry monitoring tool designed for robotics. 
This project measures UDP round trip latency, packet loss, serial link health, and per-topic publish rates to isolate hardware faults from network faults on a robot (e.g., Raspberry Pi to Base Station or STM32).

## How to Run

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Robot Simulator:**
   Open a terminal and run the simulator. This script acts as the robot (publishing ROS2 topics over UDP) and the base station (echoing ping packets).
   ```bash
   python robot_simulator.py
   ```

3. **Start UC Watcher:**
   Open a **second terminal window**, make sure it's wide enough to show the dashboard properly, and run the monitoring tool.
   ```bash
   python uc_watcher.py
   ```

## What you will see

You will see a live dashboard built with `rich`:
- **Hardware & Link Health**: Shows the round-trip latency (RTT) and packet loss to the "base station". It also simulates monitoring a UART serial link to an STM32, calculating the frame rate and logging CRC errors.
- **ROS2 Node Telemetry**: Listens to the UDP ports associated with various robot topics (`/odom`, `/cmd_vel`, etc.) and calculates their real-time publish rate (Hz), detecting dropped messages by tracking sequence numbers.

All telemetry data is actively logged to `network_health.csv` in real-time, which you can load into pandas/matplotlib later for post-run analysis.

## How to explain this in an interview (e.g., Cisco)

When demonstrating or talking about this project, focus on these key concepts that map perfectly to Systems/Networking roles:

1. **"Why did you build this?"** 
   * "In robotics, when the robot stutters or drops a command, it's hard to tell if the STM32 failed, the Raspberry Pi froze, or the WiFi link degraded. I built this tool to run alongside our main stack and provide hard data on network latency and packet loss so we stop guessing."
2. **"How does it work under the hood?"**
   * "It uses raw UDP sockets. The latency is measured by sending a timestamp payload and waiting for an echo, simulating standard ICMP ping but working entirely in user-space UDP, which is the exact same transport layer ROS2 uses (via DDS). This ensures we measure the *actual* application-layer latency, not just the OS-level route."
3. **"How does it monitor the topics?"**
   * "It binds to the UDP ports where the robot nodes publish their serialized JSON payloads. It unpacks them, tracks the sequence numbers to detect dropped packets, and calculates the sliding-window frequency (Hz)."
4. **"What happens with the data?"**
   * "It renders a real-time dashboard using `rich` for immediate visual feedback during a test run, but it also streams everything to a CSV. After a robot test, I can graph the CSV and correlate a spike in latency with a drop in publish rate on a specific node."

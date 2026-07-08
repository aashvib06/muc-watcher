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

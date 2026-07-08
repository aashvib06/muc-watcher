import socket
import threading
import time
import json
import random

# Simulator Configuration
ECHO_PORT = 9000
BASE_IP = "127.0.0.1"

# Simulated ROS2 Topics (Topic Name, Port, Publish Rate Hz)
TOPICS = [
    ("/odom", 9001, 50.0),            # 50 Hz
    ("/cmd_vel", 9002, 20.0),         # 20 Hz
    ("/camera/image_raw", 9003, 15.0),# 15 Hz
    ("/tf", 9004, 100.0),             # 100 Hz
    ("/scan", 9005, 10.0),            # 10 Hz
]

def udp_echo_server():
    """Simulates the base station replying to ping packets to measure latency."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((BASE_IP, ECHO_PORT))
    print(f"[Echo Server] Listening on {BASE_IP}:{ECHO_PORT}")
    
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            # Simulate occasional packet loss and jitter for realism
            if random.random() > 0.02:  # 2% packet loss
                time.sleep(random.uniform(0.001, 0.005))  # 1ms to 5ms jitter
                sock.sendto(data, addr)
        except Exception as e:
            print(f"Echo server error: {e}")

def simulated_ros_publisher(topic_name, port, hz):
    """Simulates a ROS2 node publishing data at a specific frequency."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    delay = 1.0 / hz
    seq = 0
    print(f"[Publisher] Topic '{topic_name}' publishing at {hz}Hz on port {port}")
    
    while True:
        payload = json.dumps({
            "topic": topic_name,
            "seq": seq,
            "timestamp": time.time()
        }).encode('utf-8')
        
        # Broadcast to localhost (UC Watcher will listen on these ports)
        # Using 127.0.0.1 since we're running locally. For a real robot, this would be multicast or the monitor's IP.
        sock.sendto(payload, (BASE_IP, port))
        seq += 1
        time.sleep(delay)

if __name__ == "__main__":
    print("Starting RoboLink Simulator...")
    
    # Start Echo Server thread
    threading.Thread(target=udp_echo_server, daemon=True).start()
    
    # Start simulated ROS topics
    for topic, port, hz in TOPICS:
        threading.Thread(target=simulated_ros_publisher, args=(topic, port, hz), daemon=True).start()
    
    print("Simulator running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")

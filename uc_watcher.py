import socket
import threading
import time
import json
import csv
from datetime import datetime
import random
import os

from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.console import Console

# Target Configuration (Match Simulator)
TARGET_IP = "127.0.0.1"
ECHO_PORT = 9000

# Topics to monitor
TOPICS = [
    ("/odom", 9001),
    ("/cmd_vel", 9002),
    ("/camera/image_raw", 9003),
    ("/tf", 9004),
    ("/scan", 9005),
]

class UCWatcher:
    def __init__(self):
        self.latency_ms = 0.0
        self.packet_loss = 0.0
        self.pings_sent = 0
        self.pings_received = 0
        
        # Topic tracking: topic -> (message_count, current_hz)
        self.topic_stats = {topic: {"count": 0, "hz": 0.0, "last_seq": -1, "drops": 0} for topic, port in TOPICS}
        
        # Serial link stats (Simulated)
        self.serial_frames_ok = 0
        self.serial_crc_errors = 0
        self.serial_hz = 0.0
        
        self.running = True
        self.log_file = open("network_health.csv", "w", newline='')
        self.csv_writer = csv.writer(self.log_file)
        self.csv_writer.writerow(["Timestamp", "Latency_ms", "Packet_Loss_%", "Serial_Hz", "Serial_Errors"] + 
                                 [f"Topic_{t}_Hz" for t, _ in TOPICS] + [f"Topic_{t}_Drops" for t, _ in TOPICS])
        
    def ping_task(self):
        """Sends UDP ping packets to measure round-trip time and packet loss."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        
        while self.running:
            start_time = time.time()
            msg = f"{start_time}".encode('utf-8')
            try:
                sock.sendto(msg, (TARGET_IP, ECHO_PORT))
                self.pings_sent += 1
                
                data, _ = sock.recvfrom(1024)
                rtt = (time.time() - float(data.decode('utf-8'))) * 1000
                
                self.latency_ms = rtt
                self.pings_received += 1
            except socket.timeout:
                pass # Packet lost
            except Exception as e:
                pass
            
            # Calculate loss over the session
            if self.pings_sent > 0:
                self.packet_loss = ((self.pings_sent - self.pings_received) / self.pings_sent) * 100
                
            time.sleep(0.1) # 10 pings per second
            
    def topic_listener(self, topic_name, port):
        """Listens to simulated ROS2 traffic and counts packets for Hz calculation."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", port))
        sock.settimeout(1.0)
        
        while self.running:
            try:
                data, _ = sock.recvfrom(1024)
                payload = json.loads(data.decode('utf-8'))
                seq = payload.get("seq", -1)
                
                # Check for dropped sequence numbers
                last_seq = self.topic_stats[topic_name]["last_seq"]
                if last_seq != -1 and seq > last_seq + 1:
                    self.topic_stats[topic_name]["drops"] += (seq - last_seq - 1)
                
                self.topic_stats[topic_name]["last_seq"] = seq
                self.topic_stats[topic_name]["count"] += 1
            except socket.timeout:
                pass
            except Exception:
                pass

    def simulated_serial_monitor(self):
        """Simulates monitoring an STM32 serial link via UART."""
        while self.running:
            # Simulate reading 100Hz serial data
            time.sleep(0.01)
            self.serial_frames_ok += 1
            if random.random() < 0.005: # 0.5% chance of CRC error on the physical line
                self.serial_crc_errors += 1

    def metrics_calculator(self):
        """Periodically calculates Hz and logs to CSV."""
        last_time = time.time()
        last_counts = {t: 0 for t, _ in TOPICS}
        last_serial_frames = 0
        
        while self.running:
            time.sleep(1.0) # Calculate every second
            current_time = time.time()
            dt = current_time - last_time
            
            # Calculate Topic Hz
            for topic, _ in TOPICS:
                count = self.topic_stats[topic]["count"]
                hz = (count - last_counts[topic]) / dt
                self.topic_stats[topic]["hz"] = hz
                last_counts[topic] = count
                
            # Calculate Serial Hz
            self.serial_hz = (self.serial_frames_ok - last_serial_frames) / dt
            last_serial_frames = self.serial_frames_ok
            
            # Write to CSV
            row = [
                datetime.now().strftime("%H:%M:%S.%f")[:-3],
                f"{self.latency_ms:.2f}",
                f"{self.packet_loss:.2f}",
                f"{self.serial_hz:.1f}",
                self.serial_crc_errors
            ]
            for topic, _ in TOPICS:
                row.append(f"{self.topic_stats[topic]['hz']:.1f}")
            for topic, _ in TOPICS:
                row.append(str(self.topic_stats[topic]['drops']))
            
            self.csv_writer.writerow(row)
            self.log_file.flush()
            
            last_time = current_time

    def generate_dashboard(self) -> Layout:
        """Builds the Rich terminal UI."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main")
        )
        layout["main"].split_row(
            Layout(name="network", ratio=1),
            Layout(name="topics", ratio=2)
        )
        
        # Header
        header = Panel(Align.center(Text("RoboLink / UC Watcher - Network Telemetry Monitor", style="bold white on blue")), style="blue")
        layout["header"].update(header)
        
        # Network & Serial Stats
        net_table = Table(show_header=False, expand=True, border_style="cyan")
        net_table.add_column("Metric", style="cyan")
        net_table.add_column("Value", justify="right")
        
        # Latency styling
        lat_style = "green" if self.latency_ms < 10 else "yellow" if self.latency_ms < 50 else "red"
        loss_style = "green" if self.packet_loss < 1 else "yellow" if self.packet_loss < 5 else "red"
        
        net_table.add_row("Base Station RTT", f"[{lat_style}]{self.latency_ms:.2f} ms[/{lat_style}]")
        net_table.add_row("WiFi Packet Loss", f"[{loss_style}]{self.packet_loss:.2f} %[/{loss_style}]")
        net_table.add_row("Ping Sent/Recv", f"{self.pings_sent} / {self.pings_received}")
        net_table.add_row("", "")
        net_table.add_row("[bold]Serial Link (STM32)[/bold]", "")
        net_table.add_row("UART Frame Rate", f"{self.serial_hz:.1f} Hz")
        net_table.add_row("Total CRC Errors", f"[red]{self.serial_crc_errors}[/red]")
        
        layout["network"].update(Panel(net_table, title="[bold]Hardware & Link Health[/bold]", border_style="cyan"))
        
        # ROS2 Topics Stats
        topic_table = Table(expand=True, border_style="magenta")
        topic_table.add_column("ROS2 Topic", style="magenta")
        topic_table.add_column("Publish Rate", justify="right")
        topic_table.add_column("Dropped Msgs", justify="right", style="red")
        
        for topic, _ in TOPICS:
            stats = self.topic_stats[topic]
            hz = stats["hz"]
            # Color code Hz (assuming 0 is bad, otherwise ok for demo)
            hz_style = "green" if hz > 0 else "red"
            topic_table.add_row(
                topic, 
                f"[{hz_style}]{hz:.1f} Hz[/{hz_style}]", 
                str(stats["drops"]) if stats["drops"] > 0 else "-"
            )
            
        layout["topics"].update(Panel(topic_table, title="[bold]ROS2 Node Telemetry[/bold]", border_style="magenta"))
        
        return layout

    def start(self):
        # Start background threads
        threading.Thread(target=self.ping_task, daemon=True).start()
        for topic, port in TOPICS:
            threading.Thread(target=self.topic_listener, args=(topic, port), daemon=True).start()
        threading.Thread(target=self.simulated_serial_monitor, daemon=True).start()
        threading.Thread(target=self.metrics_calculator, daemon=True).start()
        
        # Start UI
        console = Console()
        console.clear()
        try:
            with Live(self.generate_dashboard(), refresh_per_second=4, console=console) as live:
                while self.running:
                    time.sleep(0.25)
                    live.update(self.generate_dashboard())
        except KeyboardInterrupt:
            self.running = False
            self.log_file.close()
            print("\nShutting down UC Watcher. Data saved to network_health.csv")

if __name__ == "__main__":
    watcher = UCWatcher()
    watcher.start()

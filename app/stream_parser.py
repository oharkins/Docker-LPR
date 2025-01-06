import socket
import threading
import queue
import time
import json
import argparse

class StreamParser:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.buffer = bytearray()
        self.data_queue = queue.Queue()
        self.running = False
        self.PACKET_HEADER = b'\xbb\x0b\x00\x00'
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"Connecting to {self.host}:{self.port}")
            self.socket.connect((self.host, self.port))
            self.running = True
            
            self.process_thread = threading.Thread(target=self.process_data)
            self.process_thread.daemon = True
            self.process_thread.start()
            
            self.receive_data()
            
        except Exception as e:
            print(f"Connection error: {e}")
            self.running = False

    def receive_data(self):
        while self.running:
            try:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                self.data_queue.put(chunk)
            except Exception as e:
                print(f"Receive error: {e}")
                break
        
        self.running = False
        self.socket.close()

    def process_data(self):
        while self.running:
            try:
                while not self.data_queue.empty():
                    chunk = self.data_queue.get()
                    self.buffer.extend(chunk)
                    self.parse_buffer()
                time.sleep(0.1)
            except Exception as e:
                print(f"Processing error: {e}")

    def parse_buffer(self):
        try:
            while True:
                # Find first header
                first_header = self.buffer.find(self.PACKET_HEADER)
                if first_header == -1:
                    # No header found, keep only last byte in case it's partial header
                    self.buffer = self.buffer[-1:]
                    break
                    
                # Find next header
                next_header = self.buffer[first_header + 2:].find(self.PACKET_HEADER)
                if next_header == -1:
                    # No complete packet yet
                    break
                
                # Extract the complete packet between headers
                packet = self.buffer[first_header:first_header + next_header + 2]
                self.parse_packet(packet)
                
                # Remove processed packet from buffer
                self.buffer = self.buffer[first_header + next_header + 2:]
                
        except Exception as e:
            print(f"Parse buffer error: {e}")

    def parse_packet(self, packet):
        try:
            # Get Vehicle ID at offset 0x08
            if len(packet) >= 0x14:
                vehicle_id = packet[0x09:0x14].decode('ascii', errors='ignore').strip('\x00')
                if vehicle_id and not vehicle_id.isspace():
                    print(f"\nVehicle ID: {vehicle_id}")

            try:
                # Only look at last 200 bytes
                packet_end = packet[-200:] if len(packet) > 200 else packet
                packet_str = packet_end.decode('utf-8', errors='ignore')
                json_start = packet_str.rfind('{')
                if json_start != -1:
                    json_str = packet_str[json_start:]
                    if json_str.count('{') == 1 and '}' in json_str:  # Ensure it's a complete, single JSON object
                        print(f"JSON string: {json_str}")
            except Exception as e:
                pass

        except Exception as e:
            print(f"Packet parsing error: {e}")

    def stop(self):
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()

def parse_arguments():
    parser = argparse.ArgumentParser(description='Stream Parser')
    parser.add_argument('--host', 
                      type=str, 
                      default='166.142.83.208',
                      help='Host address (default: 166.142.83.208)')
    parser.add_argument('--port', 
                      type=int, 
                      default=5002,
                      help='Port number (default: 5002)')
    return parser.parse_args()

def main():
    args = parse_arguments()
    parser = StreamParser(host=args.host, port=args.port)
    try:
        parser.connect()
    except KeyboardInterrupt:
        print("\nShutting down...")
        parser.stop()

if __name__ == "__main__":
    main()
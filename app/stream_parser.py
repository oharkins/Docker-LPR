import socket
import threading
import queue
import time
import json
import argparse
import os
import mysql.connector

class StreamParser:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.buffer = bytearray()
        self.data_queue = queue.Queue()
        self.running = False
        self.PACKET_HEADER = b'\xbb\x0b\x00\x00'

        # Database configuration
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'mysql'),
            'user': os.getenv('MYSQL_USER', 'user'),
            'password': os.getenv('MYSQL_PASSWORD', 'password'),
            'database': os.getenv('MYSQL_DATABASE', 'stream_data')
        }

        # Initialize database connection
        self.init_database()
        
    def init_database(self):
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lpr_data (
                    vehicle_id VARCHAR(8) PRIMARY KEY,
                    make VARCHAR(50),
                    model VARCHAR(50),
                    color VARCHAR(50),
                    timestamp DATETIME,
                    INDEX (vehicle_id),
                    INDEX (timestamp)
                )
            ''')
            
            conn.commit()
            cursor.close()
            conn.close()
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Database initialization error: {e}")
            raise
        
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
    
    def upsert_vehicle_data(self, vehicle_id, make, model, color):
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            
            # Insert or update vehicle data
            query = '''
                INSERT INTO vehicle_data (vehicle_id, make, model, color)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    make = VALUES(make),
                    model = VALUES(model),
                    color = VALUES(color),
                    last_seen = CURRENT_TIMESTAMP
            '''
            cursor.execute(query, (vehicle_id, make, model, color))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"Successfully updated database for vehicle {vehicle_id}")
        except Exception as e:
            print(f"Database update error: {e}")

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

            self.db_manager.upsert_vehicle_data(vehicle_id, json_str.get('make'), json_str.get('model'), json_str.get('color'))
            print(f"Processed vehicle {vehicle_id} with data {json_str.get('make'), json_str.get('model'), json_str.get('color')}")
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
                      required=True, 
                      help='Host address')
    parser.add_argument('--port', 
                      type=int,
                      required=True, 
                      
                      help='Port number')
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
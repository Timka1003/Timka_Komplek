import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import argparse
from datetime import datetime
import time
import psutil
import threading

class PrimeServer:
    def __init__(self):
        self.active_connections = 0
        self.total_processed = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
    
    def is_prime(self, n):
        """Оптимизированная проверка простоты с использованием теста Миллера-Рабина"""
        if n <= 1:
            return False
        elif n <= 3:
            return True
        elif n % 2 == 0 or n % 3 == 0:
            return False
        
        # Тест Миллера-Рабина для больших чисел
        d = n - 1
        s = 0
        while d % 2 == 0:
            d //= 2
            s += 1
        
        for a in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]:
            if a >= n:
                continue
            x = pow(a, d, n)
            if x == 1 or x == n - 1:
                continue
            for _ in range(s - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        return True

    def process_range(self, start, end, batch_size, conn=None):
        """Обработка диапазона чисел с отправкой статуса"""
        count = 0
        current = start
        
        while current <= end:
            batch_end = min(current + batch_size - 1, end)
            
            if current <= 2 <= batch_end:
                count += 1
            
            num = current if current % 2 != 0 else current + 1
            if num > batch_end:
                break
                
            for num in range(num, batch_end + 1, 2):
                if self.is_prime(num):
                    count += 1
                
                if num % 500 == 1 and conn:
                    try:
                        conn.sendall(f"STATUS:{num}:{count}".encode())
                    except (ConnectionResetError, BrokenPipeError, OSError) as e:
                        print(f"[{datetime.now()}] Ошибка отправки STATUS: {e}")
                        break  # выходим из обработки, клиент отключён
            
            current = batch_end + 1
        
        with self.lock:
            self.total_processed += (end - start + 1)
        return count

    def handle_client(self, conn, addr):
        try:
            with self.lock:
                self.active_connections += 1
            
            conn.settimeout(300)
            data = conn.recv(1024).decode().strip()
            
            if not data:
                return
                
            if data == "status":
                stats = {
                    'active_connections': self.active_connections,
                    'total_processed': self.total_processed,
                    'uptime': time.time() - self.start_time,
                    'cpu_load': psutil.cpu_percent(),
                    'memory_usage': psutil.virtual_memory().percent
                }
                conn.sendall(str(stats).encode())
                return
                
            parts = data.split(',')
            if len(parts) != 3:
                conn.sendall(b"Invalid request format")
                return
                
            start, end, batch_size = map(int, parts)
            
            print(f"[{datetime.now()}] {addr} processing {start}-{end} (batch {batch_size})")
            
            # Обработка диапазона с отправкой промежуточных результатов
            count = self.process_range(start, end, batch_size, conn)
            
            try:
                conn.sendall(str(count).encode())
                conn.sendall(b"END")
            except Exception as e:
                print(f"[{datetime.now()}] Ошибка при отправке результата: {e}")

            print(f"[{datetime.now()}] {addr} completed: {count} primes found")
            
        except Exception as e:
            print(f"[{datetime.now()}] Error with {addr}: {str(e)}")
            try:
                conn.sendall(b"Server error")
            except:
                pass
        finally:
            with self.lock:
                self.active_connections -= 1
            try:
                conn.close()
            except:
                pass


    def distribute_range(self, start, end, chunks):
        """Распределение диапазона на части"""
        total = end - start + 1
        chunk_size = total // chunks
        return [
            (start + i * chunk_size, 
             start + (i + 1) * chunk_size - 1 if i < chunks - 1 else end)
            for i in range(chunks)
        ]

    def start_server(self, host='0.0.0.0', port=5555, max_workers=20):
        """Запуск сервера с мониторингом"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.listen()
            
            print(f"[{datetime.now()}] Server started on {host}:{port}")
            print(f"[{datetime.now()}] Max workers: {max_workers}")
            print(f"[{datetime.now()}] Server PID: {os.getpid()}")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                while True:
                    try:
                        conn, addr = s.accept()
                        print(f"[{datetime.now()}] New connection: {addr} "
                              f"(Active: {self.active_connections})")
                        executor.submit(self.handle_client, conn, addr)
                    except Exception as e:
                        print(f"[{datetime.now()}] Connection error: {str(e)}")

if __name__ == "__main__":
    import os
    
    parser = argparse.ArgumentParser(description='Оптимизированный сервер для поиска простых чисел')
    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--port', type=int, default=5555, help='Server port')
    parser.add_argument('--workers', type=int, default=20, help='Worker threads')
    
    args = parser.parse_args()
    
    server = PrimeServer()
    try:
        server.start_server(host=args.host, port=args.port, max_workers=args.workers)
    except KeyboardInterrupt:
        print(f"[{datetime.now()}] Server stopped")
    except Exception as e:
        print(f"[{datetime.now()}] Critical error: {str(e)}")

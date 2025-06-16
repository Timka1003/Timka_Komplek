import socket
from concurrent.futures import ThreadPoolExecutor
import math
import argparse
from datetime import datetime

def is_prime(n):
    """Оптимизированная проверка простоты с кэшированием маленьких простых чисел"""
    if n <= 1:
        return False
    elif n <= 3:
        return True
    elif n % 2 == 0 or n % 3 == 0:
        return False
    
    # Оптимизация: проверяем делители до квадратного корня с шагом 6k ± 1
    i = 5
    w = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += w
        w = 6 - w
    return True

def handle_client(conn, addr):
    """Обработка клиентского запроса с логированием"""
    try:
        conn.settimeout(300)  # 5 минут таймаут на обработку
        
        data = conn.recv(1024).decode().strip()
        if not data:
            return
            
        parts = data.split(',')
        if len(parts) != 3:
            conn.sendall(b"Invalid request format")
            return
            
        start, end, batch_size = map(int, parts)
        
        if start < 1 or end < start or batch_size < 1:
            conn.sendall(b"Invalid range or batch size")
            return
            
        print(f"[{datetime.now()}] Обработка {addr}: {start}-{end} (пакет {batch_size})")
        
        count = 0
        current = start
        
        # Оптимизация: обрабатываем числа пакетами
        while current <= end:
            batch_end = min(current + batch_size - 1, end)
            
            # Специальная обработка для 2 (единственное четное простое число)
            if current <= 2 <= batch_end:
                count += 1
                
            # Начинаем с нечетного числа
            num = current if current % 2 != 0 else current + 1
            if num > batch_end:
                break
                
            # Проверяем только нечетные числа
            for num in range(num, batch_end + 1, 2):
                if is_prime(num):
                    count += 1
                    
            current = batch_end + 1
            
        conn.sendall(str(count).encode())
        print(f"[{datetime.now()}] Завершено {addr}: найдено {count} простых чисел")
        
    except ValueError:
        conn.sendall(b"Invalid number format")
    except socket.timeout:
        print(f"[{datetime.now()}] Таймаут для {addr}")
        conn.sendall(b"Timeout")
    except Exception as e:
        print(f"[{datetime.now()}] Ошибка для {addr}: {str(e)}")
        conn.sendall(b"Server error")
    finally:
        conn.close()

def start_server(host='0.0.0.0', port=5555, max_workers=20):
    """Запуск сервера с настройками"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        
        print(f"[{datetime.now()}] Сервер запущен на {host}:{port}")
        print(f"[{datetime.now()}] Максимальное количество потоков: {max_workers}")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                try:
                    conn, addr = s.accept()
                    print(f"[{datetime.now()}] Подключен клиент: {addr}")
                    executor.submit(handle_client, conn, addr)
                except Exception as e:
                    print(f"[{datetime.now()}] Ошибка подключения: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Сервер для поиска простых чисел')
    parser.add_argument('--host', default='0.0.0.0', help='Адрес сервера')
    parser.add_argument('--port', type=int, default=5555, help='Порт сервера')
    parser.add_argument('--workers', type=int, default=20, help='Количество рабочих потоков')
    
    args = parser.parse_args()
    
    try:
        start_server(host=args.host, port=args.port, max_workers=args.workers)
    except KeyboardInterrupt:
        print(f"[{datetime.now()}] Сервер остановлен")

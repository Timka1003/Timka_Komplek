import socket
import math
from concurrent.futures import ThreadPoolExecutor
import argparse  # Добавляем модуль для обработки аргументов

def is_prime(n):
    """Проверка числа на простоту"""
    if n < 2:
        return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

def handle_client(conn, addr):
    """Обработка запроса от клиента"""
    with conn:
        data = conn.recv(1024).decode()
        start, end = map(int, data.split(','))
        
        count = 0
        for num in range(start, end + 1):
            if is_prime(num):
                count += 1
        
        conn.sendall(str(count).encode())

def start_server(host='0.0.0.0', port=5555):
    """Запуск сервера"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Разрешаем переиспользование адреса
        s.bind((host, port))
        s.listen()
        print(f"Сервер запущен на {host}:{port}")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            while True:
                conn, addr = s.accept()
                print(f"Подключен клиент {addr}")
                executor.submit(handle_client, conn, addr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Сервер для поиска простых чисел')
    parser.add_argument('--port', type=int, default=5555, help='Порт сервера')
    args = parser.parse_args()
    
    start_server(port=args.port)  # Используем переданный порт
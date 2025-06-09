import socket
import argparse

def distribute_range(total_start, total_end, workers):
    """Разбиение диапазона на части для воркеров"""
    total_numbers = total_end - total_start + 1
    chunk_size = total_numbers // workers
    ranges = []
    
    for i in range(workers):
        start = total_start + i * chunk_size
        end = start + chunk_size - 1 if i < workers - 1 else total_end
        ranges.append((start, end))
    
    return ranges

def get_primes_count(worker_addresses, ranges):
    """Получение количества простых чисел от воркеров"""
    results = []
    
    for (host, port), (start, end) in zip(worker_addresses, ranges):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(f"{start},{end}".encode())
            data = s.recv(1024).decode()
            results.append((f"{host}:{port}", start, end, int(data)))
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Поиск простых чисел в диапазоне')
    parser.add_argument('--start', type=int, default=0, help='Начало диапазона')
    parser.add_argument('--end', type=int, default=100, help='Конец диапазона')
    parser.add_argument('--workers', type=int, default=3, help='Количество воркеров')
    parser.add_argument('--worker-addresses', nargs='+', 
                       default=['localhost:5555', 'localhost:5556', 'localhost:5557'],
                       help='Адреса воркеров в формате host:port')
    
    args = parser.parse_args()
    
    # Преобразование адресов воркеров
    worker_addresses = []
    for addr in args.worker_addresses:
        host, port = addr.split(':')
        worker_addresses.append((host, int(port)))
    
    # Разбиение диапазона
    ranges = distribute_range(args.start, args.end, args.workers)
    
    # Получение результатов
    results = get_primes_count(worker_addresses, ranges)
    
    # Вывод статистики
    total_primes = 0
    print("\nРезультаты:")
    print("-" * 50)
    for worker, start, end, count in results:
        print(f"Воркер {worker}: диапазон {start}-{end}, найдено простых чисел: {count}")
        total_primes += count
    print("-" * 50)
    print(f"Всего найдено простых чисел: {total_primes}")

if __name__ == "__main__":
    main()
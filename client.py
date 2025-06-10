import socket
import argparse
import tkinter as tk
from tkinter import ttk, messagebox

class PrimeNumberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Поиск простых чисел")
        
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(self.main_frame, text="Начало диапазона:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.start_entry = ttk.Entry(self.main_frame)
        self.start_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        self.start_entry.insert(0, "0")
        
        ttk.Label(self.main_frame, text="Конец диапазона:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.end_entry = ttk.Entry(self.main_frame)
        self.end_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        self.end_entry.insert(0, "100")
        
        ttk.Label(self.main_frame, text="Количество воркеров:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.workers_entry = ttk.Entry(self.main_frame)
        self.workers_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        self.workers_entry.insert(0, "3")
        
        ttk.Label(self.main_frame, text="Адреса воркеров (host:port):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.workers_addresses_text = tk.Text(self.main_frame, height=4, width=30)
        self.workers_addresses_text.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        self.workers_addresses_text.insert(tk.END, "localhost:5555\nlocalhost:5556\nlocalhost:5557")

        self.run_button = ttk.Button(self.main_frame, text="Найти простые числа", command=self.run_calculation)
        self.run_button.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.result_frame = ttk.LabelFrame(self.main_frame, text="Результаты", padding="10")
        self.result_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.result_text = tk.Text(self.result_frame, height=10, width=50, state=tk.DISABLED)
        self.result_text.pack()
        
        self.progress = ttk.Progressbar(self.main_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
    
    def distribute_range(self, total_start, total_end, workers):
        total_numbers = total_end - total_start + 1
        chunk_size = total_numbers // workers
        ranges = []
        
        for i in range(workers):
            start = total_start + i * chunk_size
            end = start + chunk_size - 1 if i < workers - 1 else total_end
            ranges.append((start, end))
        
        return ranges
    
    def get_primes_count(self, worker_addresses, ranges):
        results = []
        self.progress['maximum'] = len(worker_addresses)
        self.progress['value'] = 0
        
        for i, ((host, port), (start, end)) in enumerate(zip(worker_addresses, ranges)):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)  # Таймаут 5 секунд
                    s.connect((host, port))
                    s.sendall(f"{start},{end}".encode())
                    data = s.recv(1024).decode()
                    results.append((f"{host}:{port}", start, end, int(data)))
            except Exception as e:
                results.append((f"{host}:{port}", start, end, f"Ошибка: {str(e)}"))
            
            self.progress['value'] = i + 1
            self.root.update_idletasks()
        
        return results
    
    def run_calculation(self):
        try:
            start = int(self.start_entry.get())
            end = int(self.end_entry.get())
            workers = int(self.workers_entry.get())

            if start < 0 or end < start:
                messagebox.showerror("Ошибка", "Некорректный диапазон чисел")
                return
            
            if workers <= 0:
                messagebox.showerror("Ошибка", "Количество воркеров должно быть положительным")
                return

            worker_addresses = []
            addresses_text = self.workers_addresses_text.get("1.0", tk.END).strip().split('\n')
            for addr in addresses_text:
                if addr.strip():
                    try:
                        host, port = addr.strip().split(':')
                        worker_addresses.append((host, int(port)))
                    except ValueError:
                        messagebox.showerror("Ошибка", f"Некорректный адрес воркера: {addr}")
                        return
            
            if len(worker_addresses) != workers:
                messagebox.showwarning("Предупреждение", 
                                      f"Количество воркеров ({workers}) не совпадает с количеством адресов ({len(worker_addresses)}). "
                                      "Будут использованы только первые {workers} адресов.")
                worker_addresses = worker_addresses[:workers]
            

            ranges = self.distribute_range(start, end, workers)

            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            
            results = self.get_primes_count(worker_addresses, ranges)
            
            total_primes = 0
            self.result_text.insert(tk.END, "-" * 50 + "\n")
            for worker, start, end, count in results:
                if isinstance(count, int):
                    self.result_text.insert(tk.END, f"Воркер {worker}: диапазон {start}-{end}, найдено простых чисел: {count}\n")
                    total_primes += count
                else:
                    self.result_text.insert(tk.END, f"Воркер {worker}: диапазон {start}-{end}, {count}\n")
            
            self.result_text.insert(tk.END, "-" * 50 + "\n")
            self.result_text.insert(tk.END, f"Всего найдено простых чисел: {total_primes}\n")
            self.result_text.config(state=tk.DISABLED)
            
        except ValueError:
            messagebox.showerror("Ошибка", "Пожалуйста, введите корректные числовые значения")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")

def main():
    root = tk.Tk()
    app = PrimeNumberApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

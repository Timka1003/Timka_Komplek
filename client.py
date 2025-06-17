from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import TwoLineListItem, ThreeLineListItem
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.snackbar import Snackbar
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
import socket
from threading import Thread, Lock
import random
import math
from functools import partial
import subprocess
import time
import os
from datetime import datetime
from kivy.metrics import dp



class PrimeNumberApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        self.calculation_thread = None
        self.is_calculating = False
        self.use_fast_method = True
        self.server_mode = True
        self.max_number = 10**100
        self.server_address = "localhost"
        self.server_port = 5555
        self.current_calculation_id = 0
        self.servers = {}
        self.next_port = 5555
        self.server_status = {}
        self.server_lock = Lock()
        self.server_stats = {}
        self.cache = {}



    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Blue"
        
        self.screen = MDScreen()
        root_layout = BoxLayout(orientation="vertical")

        # Top App Bar
        self.top_bar = MDTopAppBar(
            title="Поиск простых чисел [v2.1]",
            left_action_items=[["cog", lambda x: self.show_settings()]],
            right_action_items=[
                ["help-circle", lambda x: self.show_help()], 
                ["server-network", lambda x: self.show_server_settings()],
                ["server", lambda x: self.show_server_management()]
            ],
            elevation=4
        )
        root_layout.add_widget(self.top_bar)

        # Main Content
        content_layout = BoxLayout(orientation="horizontal", padding=10, spacing=10)
        self.settings_card = self.build_settings_card()
        self.results_card = self.build_results_card()
        content_layout.add_widget(self.settings_card)
        content_layout.add_widget(self.results_card)
        root_layout.add_widget(content_layout)
        self.screen.add_widget(root_layout)
        
        self.status_label = MDLabel(
            text="Готов к работе", 
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=30
        )
        root_layout.add_widget(self.status_label)
        
        return self.screen



    def build_settings_card(self):
        card = MDCard(
            orientation="vertical",
            padding=20,
            size_hint=(0.4, 1),
            elevation=3,
            radius=15
        )

        # Input Fields
        inputs = [
            ("Начало диапазона", "1", "start_input"),
            ("Конец диапазона", "1000", "end_input"),
            ("Количество потоков", "4", "workers_input"),
            ("Размер пакета", "1000", "batch_input")
        ]

        for hint, default, attr_name in inputs:
            field = MDTextField(
                hint_text=hint,
                text=default,
                input_filter="int",
                size_hint_y=None,
                height=60
            )
            setattr(self, attr_name, field)
            card.add_widget(field)

        # Buttons
        btn_box = BoxLayout(spacing=10, size_hint_y=None, height=50)
        
        self.calc_btn = MDRaisedButton(
            text="НАЧАТЬ РАСЧЕТ",
            on_release=self.toggle_calculation,
            size_hint=(0.7, 1))
        
        self.stop_btn = MDFlatButton(
            text="ОСТАНОВИТЬ",
            on_release=self.stop_calculation,
            disabled=True,
            size_hint=(0.3, 1))
        
        btn_box.add_widget(self.calc_btn)
        btn_box.add_widget(self.stop_btn)
        card.add_widget(btn_box)

        # Progress Bar
        self.progress = MDProgressBar(
            value=0,
            size_hint_y=None,
            height=6
        )
        card.add_widget(self.progress)

        # Info Label
        self.info_label = MDLabel(
            text="Макс. число: 10^100",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=30
        )
        card.add_widget(self.info_label)

        return card

    def build_results_card(self):
        card = MDCard(
            orientation="vertical", 
            padding=10, 
            size_hint=(0.6, 1), 
            elevation=3, 
            radius=15
        )

        # Results Header
        self.results_header = MDLabel(
            text="Результаты", 
            halign="center", 
            font_style="H6", 
            size_hint_y=None, 
            height=40
        )
        card.add_widget(self.results_header)

        # Scrollable Results
        self.scroll_results = ScrollView(do_scroll_x=False)
        self.results_list = BoxLayout(
            orientation="vertical", 
            size_hint_y=None, 
            spacing=5
        )
        self.results_list.bind(minimum_height=self.results_list.setter("height"))
        self.scroll_results.add_widget(self.results_list)
        card.add_widget(self.scroll_results)

        # Summary
        self.summary_label = MDLabel(
            text="", 
            halign="center", 
            font_style="Subtitle1", 
            size_hint_y=None, 
            height=40
        )
        card.add_widget(self.summary_label)

        return card

    
    def update_server_status(self, server_id, port, start, end, current, primes_found):
        """Обновляет статус сервера с правильным форматированием"""
        # Форматирование чисел с разделителями тысяч
        start_fmt = f"{start:,}".replace(",", " ")
        end_fmt = f"{end:,}".replace(",", " ")
        current_fmt = f"{current:,}".replace(",", " ")
        
        status_text = (
            f"[Сервер {server_id}] порт {port}\n"
            f"Диапазон: {start_fmt} – {end_fmt}\n"
            f"Обработано: {current_fmt}\n"
            f"Простых: {primes_found if primes_found is not None else 'расчет...'}"
        )

        # Ищем существующую метку или создаем новую
        found = False
        for child in self.server_status_container.children:
            if hasattr(child, 'server_id') and child.server_id == server_id:
                child.text = status_text
                found = True
                break

        if not found:
            label = MDLabel(
                text=status_text,
                halign="left",
                theme_text_color="Primary",
                size_hint_y=None,
                height=dp(80),  # Фиксированная высота для 4 строк
                padding=(dp(10), dp(5)),
                font_style="Body1",  # Используем стандартный шрифт
                line_height=1.0  # Стандартный межстрочный интервал
            )
            label.server_id = server_id
            self.server_status_container.add_widget(label)


    def show_settings(self):
        content = BoxLayout(orientation="vertical", spacing=15, size_hint_y=None, height=200)
        
        # Метод проверки
        method_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        method_label = MDLabel(text="Быстрый метод (Миллер-Рабин):", halign="left", size_hint_x=0.7)
        self.method_check = MDCheckbox(active=self.use_fast_method, size_hint_x=0.3)
        self.method_check.bind(active=lambda i, v: setattr(self, 'use_fast_method', v))
        method_box.add_widget(method_label)
        method_box.add_widget(self.method_check)
        
        # Режим работы
        mode_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        mode_label = MDLabel(text="Режим сервера:", halign="left", size_hint_x=0.7)
        self.mode_check = MDCheckbox(active=self.server_mode, size_hint_x=0.3)
        self.mode_check.bind(active=lambda i, v: setattr(self, 'server_mode', v))
        mode_box.add_widget(mode_label)
        mode_box.add_widget(self.mode_check)
        
        # Тема
        theme_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        theme_label = MDLabel(text="Темная тема:", halign="left", size_hint_x=0.7)
        self.theme_check = MDCheckbox(active=self.theme_cls.theme_style == "Dark", size_hint_x=0.3)
        self.theme_check.bind(active=lambda i, v: self.toggle_theme())
        theme_box.add_widget(theme_label)
        theme_box.add_widget(self.theme_check)
        
        content.add_widget(method_box)
        content.add_widget(mode_box)
        content.add_widget(theme_box)
        
        self.dialog = MDDialog(
            title="Настройки",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Закрыть", on_release=lambda x: self.dialog.dismiss())
            ]
        )
        self.dialog.open()

    def toggle_theme(self):
        self.theme_cls.theme_style = "Dark" if self.theme_cls.theme_style == "Light" else "Light"
        if hasattr(self, 'theme_check'):
            self.theme_check.active = self.theme_cls.theme_style == "Dark"

    def show_server_management(self):
        """Диалог управления серверами"""
        self.check_servers_status()  # Проверяем статус перед показом
        
        content = BoxLayout(orientation="vertical", spacing=15, size_hint_y=None, height=300)
        
        # Информация о текущих серверах
        servers_info = MDLabel(
            text="\n".join([f"Порт {port}: {info['workers']} потоков" 
                        for port, info in self.servers.items()]) or "Нактивнычх серверов нет",
            halign="center",
            size_hint_y=None,
            height=100
        )
        content.add_widget(servers_info)
        
        # Add this missing input field
        self.server_count_input = MDTextField(
            hint_text="Количество серверов",
            text="1",
            input_filter="int",
            size_hint_y=None,
            height=60
        )
        
        # Базовый порт
        self.base_port_input = MDTextField(
            hint_text="Базовый порт",
            text="5555",
            input_filter="int",
            size_hint_y=None,
            height=60
        )
        
        # Количество потоков на сервер
        self.server_workers_input = MDTextField(
            hint_text="Потоков на сервер",
            text="4",
            input_filter="int",
            size_hint_y=None,
            height=60
        )
        
        content.add_widget(self.server_count_input)
        content.add_widget(self.base_port_input)
        content.add_widget(self.server_workers_input)
        
        self.dialog = MDDialog(
            title="Управление серверами",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="Запустить", on_release=self.start_servers),
                MDRaisedButton(text="Остановить все", on_release=self.stop_all_servers)
            ]
        )
        self.dialog.open()

    def start_servers(self, *args):
        """Запуск указанного количества серверов"""
        try:
            server_count = int(self.server_count_input.text)
            base_port = int(self.base_port_input.text)
            workers = int(self.server_workers_input.text)
            
            if server_count < 1 or server_count > 10:
                self.show_error("Количество серверов должно быть от 1 до 10")
                return
                
            if base_port < 1024 or base_port > 65535:
                self.show_error("Порт должен быть в диапазоне 1024-65535")
                return
                
            if workers < 1 or workers > 20:
                self.show_error("Количество потоков должно быть от 1 до 20")
                return
            
            # Останавливаем все текущие серверы
            self.stop_all_servers()
            
            # Запускаем новые серверы
            for i in range(server_count):
                port = base_port + i
                self.start_server_instance(port, workers)
                
            self.dialog.dismiss()
            self.show_notification(f"Запущено {server_count} серверов")
            
        except ValueError:
            self.show_error("Неверный формат чисел")

    def start_server_instance(self, port, workers):
        """Запуск одного экземпляра сервера как подпроцесса"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            server_script = os.path.join(script_dir, "server.py")
            
            process = subprocess.Popen(
                ["python", server_script, "--port", str(port), "--workers", str(workers)],
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            self.servers[port] = {
                "process": process,
                "workers": workers,
                "start_time": time.time(),
                "address": "localhost" 
            }
            
            self.update_status(f"Сервер на порту {port} запущен")
            self.show_notification(f"Сервер на порту {port} запущен с {workers} потоками")
            
        except Exception as e:
            self.show_error(f"Ошибка запуска сервера: {str(e)}")
            
    def check_servers_status(self):
        """Проверка статуса всех серверов"""
        for port in list(self.servers.keys()):
            try:
                with socket.create_connection(("localhost", port), timeout=2) as sock:
                    sock.sendall(b"status")
                    response = sock.recv(1024).decode()
                    self.server_stats[port] = eval(response)
            except:
                # Сервер не отвечает, удаляем его
                self.servers.pop(port, None)
                self.show_error(f"Сервер на порту {port} не отвечает и был удален")


    def stop_all_servers(self, *args):
        """Остановка всех запущенных серверов"""
        for port, server_info in list(self.servers.items()):
            try:
                server_info["process"].terminate()
                server_info["process"].wait(timeout=3)
                self.update_status(f"Сервер на порту {port} остановлен")
            except:
                try:
                    server_info["process"].kill()
                except:
                    pass
            finally:
                self.servers.pop(port, None)
        
        if self.dialog:
            self.dialog.dismiss()
        self.show_notification("Все серверы остановлены")

    def show_server_settings(self):
        """Настройки подключения к серверам (для клиентского режима)"""
        content = BoxLayout(orientation="vertical", spacing=15, size_hint_y=None, height=150)
        
        # Адрес сервера
        self.server_addr_input = MDTextField(
            hint_text="Адрес сервера (через запятую для нескольких)",
            text=self.server_address,
            size_hint_y=None,
            height=60
        )
        
        # Базовый порт
        self.server_port_input = MDTextField(
            hint_text="Базовый порт",
            text=str(self.server_port),
            input_filter="int",
            size_hint_y=None,
            height=60
        )
        
        content.add_widget(self.server_addr_input)
        content.add_widget(self.server_port_input)
        
        self.dialog = MDDialog(
            title="Настройки серверов",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="Сохранить", on_release=self.save_server_settings)
            ]
        )
        self.dialog.open()

    def save_server_settings(self, *args):
        """Сохранение настроек подключения к серверам"""
        try:
            self.server_address = self.server_addr_input.text
            self.server_port = int(self.server_port_input.text)
            self.dialog.dismiss()
            self.show_notification("Настройки серверов сохранены")
        except ValueError:
            self.show_error("Неверный формат порта")

    def run_calculation(self, start, end, workers, batch_size, calculation_id):
        total_primes = 0
        total_numbers = end - start + 1
        
        active_servers = [(info["address"], port) for port, info in self.servers.items()]
        if not active_servers:
            Clock.schedule_once(lambda dt: self.show_error("Нет доступных серверов"))
            return

        ranges = self.distribute_range(start, end, len(active_servers))
        
        for i, (r_start, r_end) in enumerate(ranges):
            if not self.is_calculating or calculation_id != self.current_calculation_id:
                return
                
            if i >= len(active_servers):
                break
                
            address, port = active_servers[i]
            try:
                with socket.create_connection((address, port), timeout=300) as sock:
                    sock.sendall(f"{r_start},{r_end},{batch_size}".encode())
                    
                    while True:
                        try:
                            response = sock.recv(1024).decode().strip()
                        except:
                            break

                        if not response:
                            break

                        if response.startswith("STATUS:"):
                            # Убрали обновление статуса
                            continue

                        if "END" in response:
                            number_part = response.replace("END", "").strip()
                            if number_part.isdigit():
                                count = int(number_part)
                                total_primes += count
                                Clock.schedule_once(partial(
                                    self.update_results,
                                    r_start, r_end, count, total_primes,
                                    i+1, len(ranges), total_numbers
                                ))
                            break

                        elif response.strip().isdigit():
                            count = int(response.strip())
                            total_primes += count
                            Clock.schedule_once(partial(
                                self.update_results,
                                r_start, r_end, count, total_primes,
                                i+1, len(ranges), total_numbers
                            ))
                            continue

                        else:
                            print(f"[!] Неизвестный ответ от сервера: {response}")
                            break

            except Exception as e:
                error_msg = str(e)[:100]
                Clock.schedule_once(lambda dt, msg=error_msg: 
                    self.show_error(f"Ошибка сервера {port}: {msg}"))
                continue
            
        Clock.schedule_once(partial(self.finish_calculation, total_primes))



    def distribute_range(self, total_start, total_end, workers):
        """Распределение диапазона между серверами"""
        total = total_end - total_start + 1
        chunk = total // workers
        return [
            (
                total_start + i * chunk,
                total_start + (i + 1) * chunk - 1 if i < workers - 1 else total_end
            ) 
            for i in range(workers)
        ]

    def server_request(self, start, end, batch_size):
        """Отправка запроса на сервер"""
        try:
            with socket.create_connection(
                (self.server_address.strip(), self.server_port), 
                timeout=300
            ) as sock:
                sock.sendall(f"{start},{end},{batch_size}".encode())
                response = sock.recv(1024).decode()
                if response.isdigit():
                    return int(response)
                return 0
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(f"Ошибка сервера: {str(e)[:100]}"))
            return 0

    def update_results(self, start, end, count, total, current, total_workers, total_numbers, *args):
        """Обновление результатов в UI"""
        if not self.is_calculating:
            return

        # Обновление прогресса (по количеству полученных результатов)
        progress = (current / total_workers) * 100
        self.progress.value = progress

        # Элемент списка результатов
        item = TwoLineListItem(
            text=f"[{start:,} – {end:,}]",
            secondary_text=f"Найдено простых: {count}",
            theme_text_color="Primary",
            secondary_theme_text_color="Secondary"
        )
        self.results_list.add_widget(item)

        # Обновление сводки
        self.summary_label.text = f"Всего найдено: {total:,}"

        # Обновление статуса
        self.status_label.text = f"Выполнено: {current} из {total_workers} участков"

        # Скроллим вниз
        Clock.schedule_once(lambda dt: self.scroll_results.scroll_to(item), 0.1)

    def finish_calculation(self, total_primes, *args):
        """Завершение расчета"""
        if not self.is_calculating:
            return
            
        self.is_calculating = False
        self.calc_btn.text = "НАЧАТЬ РАСЧЕТ"
        self.stop_btn.disabled = True
        self.results_header.text = "Завершено"
        self.summary_label.text = f"Всего найдено простых чисел: {total_primes}"
        self.progress.value = 100
        self.update_status("Готов к работе")
        self.show_notification("Расчет завершен")

    def toggle_calculation(self, *args):
        """Переключение между началом и остановкой расчета"""
        if self.is_calculating:
            self.stop_calculation()
        else:
            self.start_calculation()

    def start_calculation(self):
        """Запуск расчета"""
        try:
            start = int(self.start_input.text)
            end = int(self.end_input.text)
            workers = int(self.workers_input.text)
            batch_size = int(self.batch_input.text)

            # Валидация ввода
            error = self.validate_input(start, end, workers, batch_size)
            if error:
                self.show_error(error)
                return

            self.current_calculation_id += 1
            self.prepare_for_calculation()
            
            # Запуск расчета в отдельном потоке
            self.calculation_thread = Thread(
                target=self.run_calculation,
                args=(start, end, workers, batch_size, self.current_calculation_id),
                daemon=True
            )
            self.calculation_thread.start()
            
            self.update_status(f"Расчет запущен (ID: {self.current_calculation_id})")
        except ValueError:
            self.show_error("Неверный формат чисел")

    def validate_input(self, start, end, workers, batch_size):
        """Проверка корректности введенных значений"""
        if start < 1:
            return "Начало диапазона должно быть ≥ 1"
        if end < start:
            return "Конец диапазона должен быть ≥ начала"
        if workers < 1 or workers > 32:
            return "Количество потоков должно быть от 1 до 32"
        if batch_size < 1 or batch_size > 100000:
            return "Размер пакета должен быть от 1 до 100000"
        if end > self.max_number:
            return f"Максимальное поддерживаемое число: 10^{int(math.log10(self.max_number))}"
        return None

    def prepare_for_calculation(self):
        """Подготовка интерфейса к расчету"""
        self.is_calculating = True
        self.results_list.clear_widgets()
        self.calc_btn.text = "ПАУЗА"
        self.stop_btn.disabled = False
        self.progress.value = 0
        self.results_header.text = "Выполняется..."
        self.summary_label.text = ""
        self.status_label.text = "" 

    def stop_calculation(self, *args):
        """Остановка расчета"""
        self.is_calculating = False
        self.calc_btn.text = "НАЧАТЬ РАСЧЕТ"
        self.stop_btn.disabled = True
        self.results_header.text = "Расчет прерван"
        self.update_status("Расчет остановлен")

    def show_help(self):
        """Показ справки"""
        help_text = """Поиск простых чисел в заданном диапазоне

Параметры:
- Начало/конец диапазона: границы поиска
- Потоки: количество серверов
- Размер пакета: чисел за одну итерацию

Режимы работы:
- Серверный: вычисления на удаленных серверах
- Можно запускать несколько серверов

Версия 2.1 | Поддержка чисел до 10^100"""
        
        self.dialog = MDDialog(
            title="Справка",
            text=help_text,
            buttons=[
                MDFlatButton(text="Закрыть", on_release=lambda x: self.dialog.dismiss())
            ]
        )
        self.dialog.open()

    def show_error(self, message):
        """Показ ошибки"""
        self.dialog = MDDialog(
            title="Ошибка",
            text=message,
            buttons=[
                MDRaisedButton(text="OK", on_release=lambda x: self.dialog.dismiss())
            ]
        )
        self.dialog.open()

    def show_notification(self, message):
        """Показ уведомления"""
        Snackbar(
            MDLabel(text=message),
            duration=2,
            size_hint_x=0.8,
            pos_hint={"center_x": 0.5},
            bg_color=self.theme_cls.primary_color
        ).open()

    def update_status(self, message):
        """Обновление статуса"""
        self.status_label.text = message

if __name__ == "__main__":
    PrimeNumberApp().run()


from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import TwoLineListItem
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.snackbar import Snackbar
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.label import MDLabel
import socket
from threading import Thread
import random
import math
from functools import partial

class PrimeNumberApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        self.calculation_thread = None
        self.is_calculating = False
        self.use_fast_method = True
        self.server_mode = False
        self.max_number = 10**100  # Максимальное поддерживаемое число
        self.server_address = "localhost"
        self.server_port = 5555
        self.current_calculation_id = 0

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Blue"
        
        self.screen = MDScreen()

        root_layout = BoxLayout(orientation="vertical")

        # Top App Bar
        self.top_bar = MDTopAppBar(
            title="Поиск простых чисел [v2.0]",
            left_action_items=[["cog", lambda x: self.show_settings()]],
            right_action_items=[["help-circle", lambda x: self.show_help()], 
                              ["server-network", lambda x: self.show_server_settings()]],
            elevation=4
        )
        root_layout.add_widget(self.top_bar)

        # Main Content
        content_layout = BoxLayout(orientation="horizontal", padding=10, spacing=10)

        # Settings Card
        self.settings_card = self.build_settings_card()
        
        # Results Card
        self.results_card = self.build_results_card()

        content_layout.add_widget(self.settings_card)
        content_layout.add_widget(self.results_card)

        root_layout.add_widget(content_layout)
        self.screen.add_widget(root_layout)
        
        # Initialize status label
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

        # Stats Label
        self.stats_label = MDLabel(
            text="", 
            halign="center", 
            theme_text_color="Secondary",
            size_hint_y=None, 
            height=30
        )
        card.add_widget(self.stats_label)

        return card

    def toggle_calculation(self, *args):
        if self.is_calculating:
            self.stop_calculation()
        else:
            self.start_calculation()

    def start_calculation(self):
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

            self.current_calculation_id += 1  # Уникальный ID для текущего расчета
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
        self.is_calculating = True
        self.results_list.clear_widgets()
        self.calc_btn.text = "ПАУЗА"
        self.stop_btn.disabled = False
        self.progress.value = 0
        self.results_header.text = "Выполняется..."
        self.summary_label.text = ""
        self.stats_label.text = ""

    def run_calculation(self, start, end, workers, batch_size, calculation_id):
        total_primes = 0
        total_numbers = end - start + 1
        ranges = self.distribute_range(start, end, workers)
        
        for i, (r_start, r_end) in enumerate(ranges):
            if not self.is_calculating or calculation_id != self.current_calculation_id:
                return
                
            if self.server_mode:
                count = self.server_request(r_start, r_end, batch_size)
            else:
                count = self.local_calculation(r_start, r_end, batch_size)
                
            total_primes += count
            
            # Обновление UI через главный поток
            Clock.schedule_once(partial(
                self.update_results,
                r_start, r_end, count, total_primes,
                i+1, len(ranges), total_numbers
            ))
        
        Clock.schedule_once(partial(self.finish_calculation, total_primes))

    def local_calculation(self, start, end, batch_size):
        count = 0
        current = start
        
        while current <= end and self.is_calculating:
            batch_end = min(current + batch_size - 1, end)
            
            # Оптимизация: пропускаем четные числа кроме 2
            if current <= 2 and batch_end >= 2:
                count += 1
            
            start_num = current if current % 2 != 0 else current + 1
            if start_num <= batch_end:
                for num in range(start_num, batch_end + 1, 2):
                    if self.use_fast_method:
                        if self.is_prime_miller_rabin(num):
                            count += 1
                    else:
                        if self.is_prime_trial_division(num):
                            count += 1
            
            current = batch_end + 1
        
        return count

    def is_prime_trial_division(self, n):
        """Оптимизированный метод пробного деления"""
        if n <= 1:
            return False
        if n <= 3:
            return True
        if n % 2 == 0 or n % 3 == 0:
            return False
        i = 5
        w = 2
        while i * i <= n:
            if n % i == 0:
                return False
            i += w
            w = 6 - w
        return True

    def is_prime_miller_rabin(self, n, k=5):
        """Улучшенный тест Миллера-Рабина"""
        if n <= 1:
            return False
        elif n <= 3:
            return True
        elif n % 2 == 0:
            return False
            
        # Записываем n-1 как d*2^s
        d = n - 1
        s = 0
        while d % 2 == 0:
            d //= 2
            s += 1

        for _ in range(k):
            a = random.randint(2, n - 2)
            x = pow(a, d, n)
            if x == 1 or x == n - 1:
                continue
            for __ in range(s - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        return True

    def server_request(self, start, end, batch_size):
        try:
            with socket.create_connection(
                (self.server_address, self.server_port), 
                timeout=300  # Увеличенный таймаут для больших диапазонов
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
        if not self.is_calculating:
            return
            
        progress = (current / total_workers) * 100
        self.progress.value = progress
        
        item = TwoLineListItem(
            text=f"Диапазон {start}-{end}",
            secondary_text=f"Простых чисел: {count}",
            theme_text_color="Primary",
            secondary_theme_text_color="Secondary"
        )
        self.results_list.add_widget(item)
        
        self.summary_label.text = f"Всего найдено: {total}"
        
        processed = min(end, int(self.end_input.text)) - int(self.start_input.text) + 1
        percent = (processed / total_numbers) * 100
        self.stats_label.text = f"Обработано: {processed:,} из {total_numbers:,} ({percent:.1f}%)"
        
        self.scroll_results.scroll_to(item)

    def finish_calculation(self, total_primes, *args):
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

    def stop_calculation(self, *args):
        self.is_calculating = False
        self.calc_btn.text = "НАЧАТЬ РАСЧЕТ"
        self.stop_btn.disabled = True
        self.results_header.text = "Расчет прерван"
        self.update_status("Расчет остановлен")

    def distribute_range(self, total_start, total_end, workers):
        total = total_end - total_start + 1
        chunk = total // workers
        return [
            (
                total_start + i * chunk,
                total_start + (i + 1) * chunk - 1 if i < workers - 1 else total_end
            ) 
            for i in range(workers)
        ]

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

    def show_server_settings(self):
        content = BoxLayout(orientation="vertical", spacing=15, size_hint_y=None, height=150)
        
        # Адрес сервера
        self.server_addr_input = MDTextField(
            hint_text="Адрес сервера",
            text=self.server_address,
            size_hint_y=None,
            height=60
        )
        
        # Порт сервера
        self.server_port_input = MDTextField(
            hint_text="Порт сервера",
            text=str(self.server_port),
            input_filter="int",
            size_hint_y=None,
            height=60
        )
        
        content.add_widget(self.server_addr_input)
        content.add_widget(self.server_port_input)
        
        self.dialog = MDDialog(
            title="Настройки сервера",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="Сохранить", on_release=self.save_server_settings)
            ]
        )
        self.dialog.open()

    def save_server_settings(self, *args):
        try:
            self.server_address = self.server_addr_input.text
            self.server_port = int(self.server_port_input.text)
            self.dialog.dismiss()
            self.show_notification("Настройки сервера сохранены")
        except ValueError:
            self.show_error("Неверный формат порта")

    def show_help(self):
        help_text = """Поиск простых чисел в заданном диапазоне

Параметры:
- Начало/конец диапазона: границы поиска
- Потоки: количество параллельных процессов
- Размер пакета: чисел за одну итерацию

Методы проверки:
1. Быстрый (Миллер-Рабин) - вероятностный метод
2. Точный (пробное деление) - медленнее, но точный

Режимы работы:
- Локальный: вычисления на этом устройстве
- Серверный: отправка запросов на сервер

Версия 2.0 | Поддержка чисел до 10^100"""
        
        self.dialog = MDDialog(
            title="Справка",
            text=help_text,
            buttons=[
                MDFlatButton(text="Закрыть", on_release=lambda x: self.dialog.dismiss())
            ]
        )
        self.dialog.open()

    def toggle_theme(self):
        self.theme_cls.theme_style = "Dark" if self.theme_cls.theme_style == "Light" else "Light"
        if hasattr(self, 'theme_check'):
            self.theme_check.active = self.theme_cls.theme_style == "Dark"

    def show_error(self, message):
        self.dialog = MDDialog(
            title="Ошибка",
            text=message,
            buttons=[
                MDRaisedButton(text="OK", on_release=lambda x: self.dialog.dismiss())
            ]
        )
        self.dialog.open()

    def show_notification(self, message):
        Snackbar(
            MDLabel(text=message),
            duration=2,
            size_hint_x=0.8,
            pos_hint={"center_x": 0.5},
            bg_color=self.theme_cls.primary_color
        ).open()

    def update_status(self, message):
        self.status_label.text = message

if __name__ == "__main__":
    PrimeNumberApp().run()

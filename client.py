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
import socket
from threading import Thread
import random
import math

class PrimeNumberApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dialog = None
        self.calculation_thread = None
        self.is_calculating = False
        self.use_fast_method = True  
        self.server_mode = False     

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"

        self.screen = MDScreen()

        root_layout = BoxLayout(orientation="vertical")

        self.top_bar = MDTopAppBar(
            title="Поиск простых чисел",
            left_action_items=[["menu", lambda x: self.show_settings()]],
            right_action_items=[["information", lambda x: self.show_help()]],
        )
        root_layout.add_widget(self.top_bar)

        content_layout = BoxLayout(orientation="horizontal", padding=10, spacing=10)

        self.settings_card = self.build_settings_card()
        self.results_card = self.build_results_card()

        content_layout.add_widget(self.settings_card)
        content_layout.add_widget(self.results_card)

        root_layout.add_widget(content_layout)

        self.screen.add_widget(root_layout)
        return self.screen

    def build_settings_card(self):
        card = MDCard(
            orientation="vertical",
            padding=20,
            size_hint=(0.4, 1),
            elevation=3,
            radius=15
        )

        self.start_input = MDTextField(
            hint_text="Начало диапазона",
            text="1",
            input_filter="int",
            size_hint_y=None,
            height=60
        )

        self.end_input = MDTextField(
            hint_text="Конец диапазона",
            text="1000",
            input_filter="int",
            size_hint_y=None,
            height=60
        )

        self.workers_input = MDTextField(
            hint_text="Потоки",
            text="4",
            input_filter="int",
            size_hint_y=None,
            height=60
        )

        self.calc_btn = MDRaisedButton(
            text="НАЧАТЬ РАСЧЕТ",
            on_release=self.toggle_calculation,
            size_hint=(1, None),
            height=50
        )

        self.stop_btn = MDFlatButton(
            text="ОСТАНОВИТЬ",
            on_release=self.stop_calculation,
            disabled=True,
            size_hint=(1, None),
            height=50
        )

        btn_box = BoxLayout(
            spacing=10,
            size_hint_y=None,
            height=50
        )
        btn_box.add_widget(self.calc_btn)
        btn_box.add_widget(self.stop_btn)

        self.progress = MDProgressBar(
            value=0,
            size_hint_y=None,
            height=6
        )

        card.add_widget(self.start_input)
        card.add_widget(self.end_input)
        card.add_widget(self.workers_input)
        card.add_widget(btn_box)
        card.add_widget(self.progress)

        return card

    def build_results_card(self):
        card = MDCard(orientation="vertical", padding=10, size_hint=(0.6, 1), elevation=3, radius=15)

        self.results_header = MDLabel(text="Результаты", halign="center", font_style="H6", size_hint_y=None, height=40)
        self.scroll_results = ScrollView()
        self.results_list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.results_list.bind(minimum_height=self.results_list.setter("height"))
        self.scroll_results.add_widget(self.results_list)
        self.summary_label = MDLabel(text="", halign="center", font_style="Subtitle1", size_hint_y=None, height=40)

        card.add_widget(self.results_header)
        card.add_widget(self.scroll_results)
        card.add_widget(self.summary_label)
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

            if start < 1 or end < start or workers < 1:
                self.show_error("Проверьте ввод")
                return

            self.prepare_for_calculation()

            self.calculation_thread = Thread(target=self.run_calculation, args=(start, end, workers), daemon=True)
            self.calculation_thread.start()
        except ValueError:
            self.show_error("Неверный формат чисел")

    def stop_calculation(self, *args):
        self.is_calculating = False
        self.calc_btn.text = "НАЧАТЬ РАСЧЕТ"
        self.stop_btn.disabled = True
        self.results_header.text = "Расчет прерван"

    def prepare_for_calculation(self):
        self.is_calculating = True
        self.results_list.clear_widgets()
        self.calc_btn.text = "ПАУЗА"
        self.stop_btn.disabled = False
        self.progress.value = 0
        self.results_header.text = "Выполняется..."
        self.summary_label.text = ""

    def run_calculation(self, start, end, workers):
        total_primes = 0
        ranges = self.distribute_range(start, end, workers)
        for i, (r_start, r_end) in enumerate(ranges):
            if not self.is_calculating:
                return
            
            if self.server_mode:
                count = self.real_server_request(r_start, r_end)
            else:
                count = self.local_calculation(r_start, r_end)
                
            total_primes += count
            Clock.schedule_once(lambda dt, s=r_start, e=r_end, c=count: self.update_results(s, e, c, total_primes, i+1, len(ranges)))
        Clock.schedule_once(lambda dt: self.finish_calculation(total_primes))

    def local_calculation(self, start, end):
        count = 0
        for num in range(start, end + 1):
            if not self.is_calculating:
                return 0
                
            if self.use_fast_method:
                if self.is_prime_miller_rabin(num):
                    count += 1
            else:
                if self.is_prime_trial_division(num):
                    count += 1
        return count

    def is_prime_trial_division(self, n):
        """Метод пробного деления (точный, но медленный для больших чисел)"""
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
        """Тест Миллера-Рабина (вероятностный, но быстрый и точен для k=5)"""
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

    def real_server_request(self, start, end):
        try:
            with socket.create_connection(("localhost", 5555), timeout=5) as sock:
                sock.sendall(f"{start},{end}".encode())
                return int(sock.recv(1024).decode())
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(f"Ошибка подключения: {e}"))
            return 0

    def update_results(self, start, end, count, total, current, total_workers):
        self.progress.value = (current / total_workers) * 100
        item = TwoLineListItem(text=f"Диапазон {start}-{end}", secondary_text=f"Простых чисел: {count}")
        self.results_list.add_widget(item)
        self.summary_label.text = f"Всего: {total}"
        self.scroll_results.scroll_to(item)

    def finish_calculation(self, total):
        self.is_calculating = False
        self.calc_btn.text = "НАЧАТЬ РАСЧЕТ"
        self.stop_btn.disabled = True
        self.results_header.text = "Завершено"
        self.summary_label.text = f"Всего найдено простых чисел: {total}"
        self.show_notification("Расчет завершен")

    def distribute_range(self, total_start, total_end, workers):
        total = total_end - total_start + 1
        chunk = total // workers
        return [(total_start + i * chunk, total_start + (i + 1) * chunk - 1 if i < workers - 1 else total_end) for i in range(workers)]

    def show_settings(self):
        box = BoxLayout(orientation="vertical", spacing=15, size_hint_y=None, height=200)
        
        theme_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        theme_label = MDLabel(text="Темная тема:", halign="left", size_hint_x=0.7)
        self.theme_check = MDCheckbox(active=self.theme_cls.theme_style == "Dark", size_hint_x=0.3)
        self.theme_check.bind(active=lambda instance, value: self.toggle_theme())
        theme_box.add_widget(theme_label)
        theme_box.add_widget(self.theme_check)
        
        method_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        method_label = MDLabel(text="Быстрый метод:", halign="left", size_hint_x=0.7)
        self.method_check = MDCheckbox(active=self.use_fast_method, size_hint_x=0.3)
        self.method_check.bind(active=lambda instance, value: setattr(self, 'use_fast_method', value))
        method_box.add_widget(method_label)
        method_box.add_widget(self.method_check)

        server_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=50)
        server_label = MDLabel(text="Режим сервера:", halign="left", size_hint_x=0.7)
        self.server_check = MDCheckbox(active=self.server_mode, size_hint_x=0.3)
        self.server_check.bind(active=lambda instance, value: setattr(self, 'server_mode', value))
        server_box.add_widget(server_label)
        server_box.add_widget(self.server_check)
        
        box.add_widget(theme_box)
        box.add_widget(method_box)
        box.add_widget(server_box)
        
        self.dialog = MDDialog(
            title="Настройки", 
            type="custom", 
            content_cls=box, 
            buttons=[MDFlatButton(text="Закрыть", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def toggle_theme(self):
        self.theme_cls.theme_style = "Dark" if self.theme_cls.theme_style == "Light" else "Light"
        if hasattr(self, 'theme_check'):
            self.theme_check.active = self.theme_cls.theme_style == "Dark"

    def show_help(self):
        help_text = """Введите диапазон, количество потоков и нажмите НАЧАТЬ РАСЧЕТ.

Доступные методы проверки:
1. Метод пробного деления (точный, но медленный)
2. Тест Миллера-Рабина (вероятностный, но быстрый)

Режимы работы:
- Локальный расчет (по умолчанию)
- Серверный расчет (требует запущенного сервера)

Настройки можно изменить в меню."""
        self.dialog = MDDialog(
            title="Справка", 
            text=help_text, 
            buttons=[MDFlatButton(text="Закрыть", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def show_error(self, message):
        self.dialog = MDDialog(
            title="Ошибка", 
            text=message, 
            buttons=[MDRaisedButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def show_notification(self, message):
        snackbar = Snackbar()
        snackbar.text = message
        snackbar.open()
           
if __name__ == "__main__":
    PrimeNumberApp().run()

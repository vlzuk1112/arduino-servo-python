import pyfirmata2
import time
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk

# --- Автоматический поиск платы Arduino ---
ports = list(serial.tools.list_ports.comports())
arduino_port = None

for p in ports:
    if "Arduino" in p.description or "USB-SERIAL" in p.description or "CH340" in p.description:
        arduino_port = p.device
        break

PORT = arduino_port if arduino_port else 'COM3'
print(f"[INFO] Подключаемся к плате на порту: {PORT}")

try:
    board = pyfirmata2.Arduino(PORT)
    servo_pin = board.get_pin('d:9:s')
except Exception as e:
    print(f"[ERROR] Не удалось подключиться: {e}")
    exit()

# --- Функции управления сервоприводом ---
def send_angle(angle):
    """Отправка угла на Arduino и обновление текста в интерфейсе"""
    # Сначала переводим строку в float, а затем в целое число int
    angle = int(float(angle)) 
    servo_pin.write(angle)
    value_label.config(text=f"Текущий угол: {angle}°")


def set_fixed_angle(angle):
    """Функция для кнопок фиксированного угла"""
    slider.set(angle)  # Сдвигаем ползунок, он сам вызовет send_angle
    send_angle(angle)

# --- Создание графического интерфейса (GUI) ---
root = tk.Tk()
root.title("Управление сервоприводом")
root.geometry("400x250")
root.resizable(False, False)

# Стили для красивого отображения
style = ttk.Style()
style.theme_use('clam')

# Заголовок
title_label = ttk.Label(root, text="Управление Сервоприводом", font=("Arial", 14, "bold"))
title_label.pack(pady=10)

# Ползунок (Слайдер) для плавной регулировки
slider = ttk.Scale(root, from_=0, to=180, orient="horizontal", command=send_angle)
slider.set(90)  # Стартовое положение по центру
slider.pack(fill="x", padx=30, pady=10)

# Текст, показывающий текущий угол
value_label = ttk.Label(root, text="Текущий угол: 90°", font=("Arial", 11))
value_label.pack(pady=5)

# Фрейм (контейнер) для кнопок быстрого выбора
button_frame = ttk.Frame(root)
button_frame.pack(pady=15)

# Кнопки быстрого выбора углов
btn_0 = ttk.Button(button_frame, text="0°", command=lambda: set_fixed_angle(0))
btn_0.pack(side="left", padx=5)

btn_90 = ttk.Button(button_frame, text="90°", command=lambda: set_fixed_angle(90))
btn_90.pack(side="left", padx=5)

btn_180 = ttk.Button(button_frame, text="180°", command=lambda: set_fixed_angle(180))
btn_180.pack(side="left", padx=5)

# Обработка закрытия окна
def on_closing():
    print("[INFO] Закрытие программы...")
    board.exit()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

# Запуск цикла обработки интерфейса
print("[SUCCESS] Графический интерфейс запущен!")
root.mainloop()

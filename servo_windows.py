import pyfirmata2
import time
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk
import threading

# --- Автопоиск Arduino ---
ports = list(serial.tools.list_ports.comports())
arduino_port = None
for p in ports:
    if any(x in p.description for x in ["Arduino", "USB-SERIAL", "CH340"]):
        arduino_port = p.device
        break

PORT = arduino_port if arduino_port else 'COM3'
print(f"[INFO] Подключение к автоматической линии на порту: {PORT}")

try:
    board = pyfirmata2.Arduino(PORT)
    # Настраиваем 3 привода на пины 9, 10 и 11
    servo1 = board.get_pin('d:9:s')   # Серво 1: Конвейер
    servo2 = board.get_pin('d:10:s')  # Серво 2: Сортировщик
    servo3 = board.get_pin('d:11:s')  # Серво 3: Толкатель
except Exception as e:
    print(f"[ERROR] Ошибка подключения линии: {e}")
    exit()

# Флаг для работы автоматического режима
auto_mode_active = False

def send_angle(servo_obj, label_obj, angle):
    """Отправка угла на конкретный привод"""
    angle = int(float(angle))
    servo_obj.write(angle)
    label_obj.config(text=f"{angle}°")

# --- Логика автоматической линии ---
def automation_loop():
    """Цикл работы автоматической линии (в отдельном потоке)"""
    global auto_mode_active
    print("[INFO] Автоматическая линия запущена")
    
    try:
        while auto_mode_active:
            # Сценарий линии:
            # 1. Запуск конвейера (Серво 1 в 180°)
            slider1.set(180); send_angle(servo1, val_lbl1, 180)
            time.sleep(1.5)
            if not auto_mode_active: break
            
            # 2. Срабатывание толкателя (Серво 3 резко на 90° и обратно)
            slider3.set(90); send_angle(servo3, val_lbl3, 90)
            time.sleep(0.5)
            slider3.set(0); send_angle(servo3, val_lbl3, 0)
            time.sleep(0.5)
            if not auto_mode_active: break
            
            # 3. Поворот сортировщика (Серво 2 на 45°)
            slider2.set(45); send_angle(servo2, val_lbl2, 45)
            time.sleep(1.0)
            slider2.set(0); send_angle(servo2, val_lbl2, 0)
            time.sleep(0.5)
            
    except Exception as e:
        print(f"[ERROR] Сбой в автоматическом цикле: {e}")

def toggle_auto_mode():
    """Включение / выключение автоматики"""
    global auto_mode_active
    if not auto_mode_active:
        auto_mode_active = True
        btn_auto.config(text="СТОП ЛИНИЯ", style="Stop.TButton")
        # Запускаем автоматику в отдельном потоке, чтобы окно интерфейса не зависало
        threading.Thread(target=automation_loop, daemon=True).start()
    else:
        auto_mode_active = False
        btn_auto.config(text="ЗАПУСТИТЬ АВТОМАТИКУ", style="TButton")
        print("[INFO] Автоматическая линия остановлена оператором")

# --- Интерфейс Tkinter ---
root = tk.Tk()
root.title("Управление автоматической линией")
root.geometry("450x400")
root.resizable(False, False)

style = ttk.Style()
style.theme_use('clam')
style.configure("Stop.TButton", foreground="white", background="red")

ttk.Label(root, text="Панель управления конвейером", font=("Arial", 14, "bold")).pack(pady=10)

# Функция-помощник для создания блоков управления приводами
def create_servo_ui(title, servo_obj, start_val):
    frame = ttk.LabelFrame(root, text=title, padding=10)
    frame.pack(fill="x", padx=20, pady=5)
    
    lbl_val = ttk.Label(frame, text=f"{start_val}°", font=("Arial", 10, "bold"), width=6)
    lbl_val.pack(side="right", padx=5)
    
    sld = ttk.Scale(frame, from_=0, to=180, orient="horizontal", 
                    command=lambda v: send_angle(servo_obj, lbl_val, v))
    sld.set(start_val)
    sld.pack(fill="x", expand=True, padx=5)
    return sld, lbl_val

# Создаем элементы управления для 3-х приводов
slider1, val_lbl1 = create_servo_ui("Серво 1: Конвейерная лента", servo1, 0)
slider2, val_lbl2 = create_servo_ui("Серво 2: Распределитель (Сортировка)", servo2, 0)
slider3, val_lbl3 = create_servo_ui("Серво 3: Физический толкатель", servo3, 0)

# Большая кнопка запуска автоматики
btn_auto = ttk.Button(root, text="ЗАПУСТИТЬ АВТОМАТИКУ", command=toggle_auto_mode, width=30)
btn_auto.pack(pady=25)

def on_closing():
    global auto_mode_active
    auto_mode_active = False
    board.exit()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()


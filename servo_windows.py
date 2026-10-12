import pyfirmata2
import time
import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk
import threading

# --- Умный автопоиск двух плат Arduino ---
ports = list(serial.tools.list_ports.comports())
firmata_port = None
hmi_port = None

print("[INFO] Сканирование портов системы...")
for p in ports:
    if any(x in p.description for x in ["Arduino", "USB-SERIAL", "CH340"]):
        # Проверяем, занят ли порт Firmata, или пытаемся распределить
        if not firmata_port:
            firmata_port = p.device
        else:
            hmi_port = p.device

# Если автопоиск не распределил порты, можно задать их вручную в качестве подстраховки:
if not hmi_port and firmata_port:
    # Предположим, что если определился один, второй — следующий или предыдущий порт
    print("[WARNING] Найдена только одна плата автопоиском. Проверьте подключение второй.")

# Настройки портов по умолчанию, если платы не определились автоматически
if not firmata_port: firmata_port = 'COM3'
if not hmi_port: hmi_port = 'COM4'

# --- Инициализация Первой Arduino (Исполнительная линия Firmata) ---
try:
    board = pyfirmata2.Arduino(firmata_port)
    servo1 = board.get_pin('d:9:s')  
    servo2 = board.get_pin('d:10:s') 
    servo3 = board.get_pin('d:11:s') 
    print(f"[SUCCESS] Первая Arduino (Линия) подключена на порту {firmata_port}")
except Exception as e:
    print(f"[ERROR] Не удалось подключить Исполнительную плату: {e}")
    exit()

# --- Инициализация Второй Arduino (HMI / Физическая Кнопка) ---
hmi_serial = None
try:
    hmi_serial = serial.Serial(hmi_port, 9600, timeout=0.1)
    print(f"[SUCCESS] Вторая Arduino (HMI Кнопка) подключена на порту {hmi_port}")
except Exception as e:
    print(f"[WARNING] Физическая плата HMI не найдена на {hmi_port}: {e}")
    print("[INFO] Скрипт запущен в режиме программной симуляции E-Stop.")

# Глобальные флаги состояний линии
auto_mode_active = False
emergency_active = False

def send_angle(servo_obj, label_obj, angle):
    """Отправка угла на выбранный привод с защитой от изменения при аварии"""
    if emergency_active: return  
    angle = int(float(angle))
    servo_obj.write(angle)
    label_obj.config(text=f"{angle}°")

# --- Поток непрерывного считывания физической кнопки ---

def hmi_listener():
    global emergency_active, auto_mode_active
    if not hmi_serial: return
    
    print("[INFO] Поток считывания физической кнопки E-Stop запущен.")
    while True:
        try:
            if hmi_serial.in_waiting > 0:
                line = hmi_serial.readline().decode('utf-8').strip()
                
                if line == "EMERGENCY_STOP":
                    print("[⚠️ CRITICAL] Аварийный стоп с физической панели!")
                    root.after(0, trigger_emergency_stop)
                    
                elif line == "RESET_EMERGENCY":
                    print("[🔄 SYSTEM] Получен физический сигнал сброса аварии.")
                    # Безопасно закрываем красное окно из потока Tkinter
                    root.after(0, dismiss_emergency)
                    
        except Exception as e:
            print(f"[ERROR] Ошибка чтения HMI-порта: {e}")
            break
        time.sleep(0.05)


# --- Логика Аварийного Останова (E-Stop) ---
def trigger_emergency_stop():
    global auto_mode_active, emergency_active
    if emergency_active: return # Игнорируем повторные нажатия
    
    auto_mode_active = False  # Мгновенно разрываем цикл автоматики конвейера
    emergency_active = True
    print("[🚨 SYSTEM] АВАРИЙНЫЙ ОСТАНОВ АКТИВИРОВАН!")
    
    # Мгновенно переводим все сервоприводы линии в безопасное положение (0 градусов)
    try:
        servo1.write(0); val_lbl1.config(text="0°"); slider1.set(0)
        servo2.write(0); val_lbl2.config(text="0°"); slider2.set(0)
        servo3.write(0); val_lbl3.config(text="0°"); slider3.set(0)
    except Exception as e:
        print(f"[WARNING] Ошибка перевода сервоприводов в безопасный режим: {e}")
    
    # Блокируем кнопку запуска на основном экране
    btn_auto.config(text="ЛИНИЯ ЗАБЛОКИРОВАНА", state="disabled")
    
    # Открываем аварийное модальное окно поверх экрана
    show_emergency_overlay()

def show_emergency_overlay():
    global overlay
    overlay = tk.Toplevel(root)
    overlay.title("🚨 АВАРИЙНЫЙ ОСТАНОВ ЛИНИИ")
    overlay.geometry("450x400")
    overlay.configure(bg="#d9534f") # Яркий аварийный красный цвет
    overlay.grab_set()  # Перехватывает фокус и блокирует клики по главному окну
    
    # Запрещаем закрывать аварийный экран на крестик, требуем осознанный сброс аварии
    overlay.protocol("WM_DELETE_WINDOW", lambda: None) 
    
    lbl_warn = tk.Label(overlay, text="⚠️ ВНИМАНИЕ! ⚠️\n\nНАЖАТА ФИЗИЧЕСКАЯ КНОПКА\nАВАРИЙНОГО ОСТАНОВА", 
                        fg="white", bg="#d9534f", font=("Arial", 16, "bold"), justify="center")
    lbl_warn.pack(expand=True)
    
    btn_reset = tk.Button(overlay, text="СБРОСИТЬ АВАРИЮ (RESET)", font=("Arial", 12, "bold"),
                          bg="white", fg="#d9534f", activebackground="#f5f5f5",
                          command=dismiss_emergency, padding=10)
    btn_reset.pack(pady=40)

def dismiss_emergency():
    global emergency_active
    emergency_active = False
    btn_auto.config(text="ЗАПУСТИТЬ АВТОМАТИКУ", state="normal", style="TButton")
    overlay.destroy()
    print("[INFO] Аварийный режим успешно сброшен оператором. Линия готова к работе.")

# --- Поток автоматической конвейерной линии ---
def automation_loop():
    global auto_mode_active
    print("[INFO] Конвейерная линия запущена в автоматическом режиме.")
    try:
        while auto_mode_active:
            # Сценарий автоматизации конвейера
            slider1.set(180); send_angle(servo1, val_lbl1, 180)
            time.sleep(1.5)
            if not auto_mode_active: break
            
            slider3.set(90); send_angle(servo3, val_lbl3, 90)
            time.sleep(0.5)
            slider3.set(0); send_angle(servo3, val_lbl3, 0)
            time.sleep(0.5)
            if not auto_mode_active: break
            
            slider2.set(45); send_angle(servo2, val_lbl2, 45)
            time.sleep(1.0)
            slider2.set(0); send_angle(servo2, val_lbl2, 0)
            time.sleep(0.5)
    except Exception as e:
        print(f"[ERROR] Критический сбой автоматического цикла: {e}")

def toggle_auto_mode():
    global auto_mode_active
    if emergency_active: return
    if not auto_mode_active:
        auto_mode_active = True
        btn_auto.config(text="СТОП ЛИНИЯ", style="Stop.TButton")
        # Запускаем конвейер в отдельном потоке, чтобы окно программы не зависало
        threading.Thread(target=automation_loop, daemon=True).start()
    else:
        auto_mode_active = False
        btn_auto.config(text="ЗАПУСТИТЬ АВТОМАТИКУ", style="TButton")

# --- Построение интерфейса Tkinter ---
root = tk.Tk()
root.title("HMI Панель: Управление автоматической линией")
root.geometry("460x440")
root.resizable(False, False)

style = ttk.Style()
style.theme_use('clam')
style.configure("Stop.TButton", foreground="white", background="#d9534f")

ttk.Label(root, text="Панель оператора конвейера", font=("Arial", 14, "bold")).pack(pady=10)

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

slider1, val_lbl1 = create_servo_ui("Серво 1: Конвейерная лента", servo1, 0)
slider2, val_lbl2 = create_servo_ui("Серво 2: Распределитель (Сортировка)", servo2, 0)
slider3, val_lbl3 = create_servo_ui("Серво 3: Физический толкатель", servo3, 0)

btn_auto = ttk.Button(root, text="ЗАПУСТИТЬ АВТОМАТИКУ", command=toggle_auto_mode, width=30)
btn_auto.pack(pady=15)

# Программная кнопка-дублер E-Stop на экране ПК
btn_gui_estop = tk.Button(root, text="🚨 ЭКСТРЕННЫЙ СТОП (ПРОГРАММНЫЙ)", bg="darkred", fg="white", 
                          font=("Arial", 10, "bold"), command=trigger_emergency_stop, pady=5)
btn_gui_estop.pack(fill="x", padx=20, pady=5)

def on_closing():
    global auto_mode_active
    auto_mode_active = False
    if hmi_serial: hmi_serial.close()
    board.exit()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

# Запуск фонового асинхронного потока для непрерывного опроса физического COM-порта кнопки
threading.Thread(target=hmi_listener, daemon=True).start()

root.mainloop()



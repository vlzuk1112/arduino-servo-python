import pyfirmata2
import time
import serial.tools.list_ports

# Автоматически находим порт, к которому подключена Arduino
ports = list(serial.tools.list_ports.comports())
arduino_port = None

for p in ports:
    if "Arduino" in p.description or "USB-SERIAL" in p.description or "CH340" in p.description:
        arduino_port = p.device
        break

# Если автопоиск не сработал, жестко укажем порт (измените на свой, если нужно)
PORT = arduino_port if arduino_port else 'COM3'
print(f"[INFO] Подключаемся к плате на порту: {PORT}")

try:
    board = pyfirmata2.Arduino(PORT)
    # Настраиваем 9-й пин в режим работы с сервоприводом (SERVO)
    servo_pin = board.get_pin('d:9:s')
except Exception as e:
    print(f"[ERROR] Не удалось подключиться к плате: {e}")
    print("Убедитесь, что на плату загружен скетч StandardFirmata из Arduino IDE, а порт свободен.")
    exit()

def set_angle(angle):
    servo_pin.write(angle)
    time.sleep(0.01)

print("[SUCCESS] Скрипт запущен! Нажмите Ctrl+C для выхода.")
try:
    while True:
        # Поворот от 0 до 180 градусов
        for angle in range(0, 180, 1):
            set_angle(angle)
        # Поворот обратно от 180 до 0 градусов
        for angle in range(180, 0, -1):
            set_angle(angle)
except KeyboardInterrupt:
    print("\n[INFO] Выход из программы...")
    board.exit()

import sys
import threading
import serial
import serial.tools.list_ports
from PyQt5 import QtWidgets
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import pyqtSignal, Qt
from ports import Ui_COM_ports_program
from PyQt5.QtCore import QTimer


def serial_ports():
    ports = ['COM%s' % (i + 1) for i in range(256)]
    result = []
    for port in ports:
        try:
            s = serial.Serial(port, 9600)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


class ReadThread:
    data_received = pyqtSignal(bytes)

    def __init__(self, serial_port):
        self.serial_port = serial_port
        self.thread = threading.Thread(target=self.run)
        self.running = False

    def start(self):
        self.running = True
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def run(self):
        try:
            while self.running:
                if self.serial_port.is_open and self.serial_port.in_waiting:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    self.data_received.emit(data)
        except serial.SerialException:
            pass


class CustomTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace:
            cursor = self.textCursor()
            if cursor.position() == len(self.toPlainText()):
                cursor.movePosition(QTextCursor.End)
                self.setTextCursor(cursor)
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)


class ComPortSettings:
    def __init__(self):
        self.settings = {
            'port_name': None,
            'baudrate': 9600,
            'stopbits': serial.STOPBITS_ONE,
            'bytesize': serial.EIGHTBITS,
            'parity': serial.PARITY_NONE,
            'flow_control': False,
            'read_timeout': None,
            'write_timeout': None
        }

    def set_port_name(self, port_name):
        self.settings['port_name'] = port_name

    def set_baudrate(self, baudrate):
        self.settings['baudrate'] = baudrate

    def set_stopbits(self, stopbits):
        self.settings['stopbits'] = stopbits

    def set_bytesize(self, bytesize):
        self.settings['bytesize'] = bytesize

    def set_parity(self, parity):
        self.settings['parity'] = parity

    def set_flow_control(self, flow_control):
        self.settings['flow_control'] = flow_control

    def set_read_timeout(self, read_timeout):
        self.settings['read_timeout'] = read_timeout

    def set_write_timeout(self, write_timeout):
        self.settings['write_timeout'] = write_timeout

    def get_port_name(self):
        return self.settings['port_name']


class COMPortsProgram(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_COM_ports_program()
        self.ui.setupUi(self)

        self.serial_port = None  # Инициализация serial_port

        self.com_port_settings = ComPortSettings()
        self.read_thread = None

        # Connect events and handlers
        self.ui.clear.clicked.connect(self.clear_data)
        self.ui.name_com_ports.currentTextChanged.connect(self.update_com_port)
        self.ui.input.textChanged.connect(self.send_data)

        self.update_com_ports()
        self.auto_detect_port()
        self.update_ui_from_settings()

        # Initialize QTimer for periodic updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)  # Update every second

    def auto_detect_port(self):
        com_ports = serial_ports()
        if com_ports:
            self.com_port_settings.set_port_name(com_ports[0])

    def update_com_ports(self):
        com_ports = serial_ports()
        self.ui.name_com_ports.clear()
        self.ui.name_com_ports.addItems(com_ports)

    def update_com_port(self):
        com_port = self.ui.name_com_ports.currentText()
        self.com_port_settings.set_port_name(com_port)

    #def start_communication(self):
      #  input_text = self.ui.input.toPlainText()
       # self.send_data(input_text)

    def update_ui_from_settings(self):
        self.ui.name_com_ports.setCurrentText(self.com_port_settings.get_port_name())

    def update_status(self):
        port_name = self.com_port_settings.get_port_name()
        if port_name:
            try:
                s = serial.Serial(port_name)
                baudrate = s.baudrate
                bytes_received = s.in_waiting
                s.close()
                status_info = f"COM Port Speed: {baudrate} bps\nBytes Received: {bytes_received}"
                self.ui.status_input.setPlainText(status_info)
            except (OSError, serial.SerialException):
                pass

    def connect_port(self):
        port_name = self.com_port_settings.get_port_name()
        if port_name:
            try:
                if self.serial_port:
                    self.disconnect_port()

                self.serial_port = serial.Serial(
                    port_name,
                    self.com_port_settings.settings['baudrate'],
                    stopbits=self.com_port_settings.settings['stopbits'],
                    bytesize=self.com_port_settings.settings['bytesize'],
                    parity=self.com_port_settings.settings['parity'],
                    xonxoff=self.com_port_settings.settings['flow_control'],
                    timeout=self.com_port_settings.settings['read_timeout'],
                    write_timeout=self.com_port_settings.settings['write_timeout']
                )

                self.ui.input.setEnabled(True)
                self.ui.input.setFocus()

                self.read_thread = ReadThread(self.serial_port)
                self.read_thread.data_received.connect(self.on_data_received)
                self.read_thread.start()

            except serial.SerialException as e:
                QtWidgets.QMessageBox.critical(self, 'Error', str(e))

    def on_data_received(self, data):
        current_bytes_received = int(self.ui.bytes_received.text()) + len(data)
        self.ui.bytes_received.setText(str(current_bytes_received))

        cursor = self.ui.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.ui.output.setTextCursor(cursor)
        self.ui.output.insertPlainText(data.decode())

    def disconnect_port(self):
        if self.serial_port:
            self.read_thread.stop()
            self.serial_port.close()
            self.serial_port = None

    def send_data(self):
        # Отправка данных через COM-порт
        if self.serial_port:
            text = self.ui.input.toPlainText()
            if text:
                last_char = text[-1]
                self.serial_port.write(last_char.encode())

    def read_data(self):
        # Чтение данных из COM-порта и вывод в окно вывода
        if self.serial_port:
            data = self.serial_port.read().decode()
            self.ui.output.insertPlainText(data)
            self.ui.bytes_received.setText(
                str(int(self.ui.bytes_received.text()) + 1))

    def closeEvent(self, event):
        if self.serial_port:
            self.read_thread.stop()
            self.serial_port.close()
            self.serial_port = None
        super().closeEvent(event)

    def clear_data(self):
        self.ui.input.clear()
        self.ui.output.clear()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    window = COMPortsProgram()
    window.show()

    com_ports = serial_ports()

    if com_ports:
        port_info = "Available COM ports:\n" + ", ".join(com_ports)
    else:
        port_info = "No COM ports found!"

    debug_line_edit = window.ui.debug
    debug_line_edit.setText(port_info)

    sys.exit(app.exec_())

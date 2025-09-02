import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import serial
import serial.tools.list_ports
import struct
import base64
import io

SPEED = 0
DIST  = 1
ACCEL = 2
DECEL = 3
SPDKP = 4
SPDKI = 5
TRQKP = 6
TRQKI = 7

SEND = 1
GET = 0

def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def get_crc(buf, length):
    CRC_POL = 0xDB
    size = 4 + length
    dividend = buf[0]

    for i in range(1, size):
        next_div = buf[i]
        for j in range(8):
            if dividend & 0x80:
                dividend ^= CRC_POL
            else:
                dividend ^= 0

            if ((i == size - 1) and (j == 7)):
                break

            dividend <<= 1
            dividend &= 0xFF

            if next_div & 0x80:
                dividend |= 0x01

            next_div <<= 1
            next_div &= 0xFF

    return (dividend << 1) & 0xFF

def send_hex_cmd_frame(cmd_dir, index):
    port = com_port_var.get()
    baud = int(baud_rate_var.get())
    try:
        timeout = float(timeout_var.get())
    except ValueError:
        messagebox.showerror("Invalid Timeout", "Please enter a valid number for timeout.")
        return
    
    crcZeroByte = b'\x00'

    if cmd_dir == SEND:
        float_str = float_entries[index].get().strip()
        try:
            float_value = float(float_str)
            float_bytes = struct.pack('<f', float_value)
        except ValueError:
            messagebox.showerror("Invalid Input", f"{label_vars[index].get()}: Please enter a valid float value.")
            return
        
        if index == SPEED:
            if float_value < 3 or float_value > 1016:
                messagebox.showerror("Out of Range", f"{label_vars[index].get()}: Value must be between 3 and 1016.")
                return
        elif index == DIST:
            if float_value < 0 or float_value > 400:
                messagebox.showerror("Out of Range", f"{label_vars[index].get()}: Value must be between 0 and 400.")
                return
        elif index == ACCEL:
            if float_value < 118.110236 or float_value > 1000000:
                messagebox.showerror("Out of Range", f"{label_vars[index].get()}: Value must be between 118.110236 and 1e+6.")
                return
        elif index == DECEL:
            if float_value < 118.110236 or float_value > 1000000:
                messagebox.showerror("Out of Range", f"{label_vars[index].get()}: Value must be between 118.110236 and 1e+6.")
                return
        elif index == SPDKP:
            if float_value > 30000:
                messagebox.showerror("Out of Range", f"{label_vars[index].get()}: Value must be less than 30000.")
                return
        elif index == SPDKI:
            if float_value > 4000:
                messagebox.showerror("Out of Range", f"{label_vars[index].get()}: Value must be less than 4000.")
                return
        elif index == TRQKP:
            if float_value > 9000:
                messagebox.showerror("Out of Range", f"{label_vars[index].get()}: Value must be less than 9000.")
                return
        elif index == TRQKI:
            if float_value > 2100:
                messagebox.showerror("Out of Range", f"{label_vars[index].get()}: Value must be less than 2100.")
                return
        else:
            return

        prefix_map = {
            SPEED: "01 02 05 02",
            DIST : "01 01 05 02",
            ACCEL: "01 0A 05 02",
            DECEL: "01 0B 05 02",
            SPDKP: "01 11 05 02",
            SPDKI: "01 12 05 02",
            TRQKP: "01 13 05 02",
            TRQKI: "01 14 05 02",
        }
        prefix_bytes = bytes.fromhex(prefix_map.get(index, "01 00 05 02"))
        crc = get_crc(prefix_bytes + float_bytes + crcZeroByte, 5)
        
    else:
        prefix_map = {
            SPEED: "01 02 01 01",
            DIST : "01 01 01 01",
            ACCEL: "01 0A 01 01",
            DECEL: "01 0B 01 01",
            SPDKP: "01 11 01 01",
            SPDKI: "01 12 01 01",
            TRQKP: "01 13 01 01",
            TRQKI: "01 14 01 01",
        }
        prefix_bytes = bytes.fromhex(prefix_map.get(index, "01 00 01 01"))
        crc = get_crc(prefix_bytes + crcZeroByte, 1)
        
    suffix_bytes = bytes.fromhex(f"{crc:02X}")

    try:
        with serial.Serial(port, baud, timeout=timeout) as ser:
            response_texts[0].tag_configure("send", foreground="green")
            response_texts[0].tag_configure("get", foreground="#8B27B3")
            response_texts[0].tag_configure("fail", foreground="red")
            if cmd_dir == SEND:
                ser.write(prefix_bytes + float_bytes + suffix_bytes)
                response = ser.read(64)
                if response:
                    if response == b'\x01\x01\x01\x00\xE0':
                        response_texts[0].insert(tk.END, "Distance is set to " + float_str + " mm.\n", "send")
                    elif response == b'\x01\x02\x01\x00\x20':
                        response_texts[0].insert(tk.END, "Speed is set to " + float_str + " mm/min.\n", "send")
                    elif response == b'\x01\x0A\x01\x00\xFA':
                        response_texts[0].insert(tk.END, "Acceleration is set to " + float_str + " rpm/s.\n", "send")
                    elif response == b'\x01\x0B\x01\x00\xBA':
                        response_texts[0].insert(tk.END, "Deceleration is set to " + float_str + " rpm/s.\n", "send")
                    elif response == b'\x01\x11\x01\x00\xE2':
                        response_texts[0].insert(tk.END, "Speed Kp is set to " + float_str + ".\n", "send")
                    elif response == b'\x01\x12\x01\x00\x22':
                        response_texts[0].insert(tk.END, "Speed Ki is set to " + float_str + ".\n", "send")
                    elif response == b'\x01\x13\x01\x00\x62':
                        response_texts[0].insert(tk.END, "Torque Kp is set to " + float_str + ".\n", "send")
                    elif response == b'\x01\x14\x01\x00\x14':
                        response_texts[0].insert(tk.END, "Torque Ki is set to " + float_str + ".\n", "send")
                    else:
                        response_texts[0].insert(tk.END, "Error! Please try again.\n", "fail")
                else:
                    response_texts[0].insert(tk.END, "No response received.\n")

            else:
                ser.write(prefix_bytes + suffix_bytes)
                response = ser.read(64)
                if response:
                    float_value = struct.unpack('<f', response[3:7])[0]
                    float_str = str(f"{float_value:.2f}")
                    if response[1:2] == b'\x01':
                        response_texts[0].insert(tk.END, "Get Distance Value: " + float_str + " mm.\n", "get")
                    elif response[1:2] == b'\x02':
                        response_texts[0].insert(tk.END, "Get Speed Value: " + float_str + " mm/min.\n", "get")
                    elif response[1:2] == b'\x0A':
                        response_texts[0].insert(tk.END, "Get Acceleration Value: " + float_str + " rpm/s.\n", "get")
                    elif response[1:2] == b'\x0B':
                        response_texts[0].insert(tk.END, "Get Deceleration Value: " + float_str + " rpm/s.\n", "get")
                    elif response[1:2] == b'\x11':
                        response_texts[0].insert(tk.END, "Get Speed Kp Value: " + str(int(float_value)) + ".\n", "get")
                    elif response[1:2] == b'\x12':
                        response_texts[0].insert(tk.END, "Get Speed Ki Value: " + str(int(float_value)) + ".\n", "get")
                    elif response[1:2] == b'\x13':
                        response_texts[0].insert(tk.END, "Get Torque Kp Value: " + str(int(float_value)) + ".\n", "get")
                    elif response[1:2] == b'\x14':
                        response_texts[0].insert(tk.END, "Get Torque Ki Value: " + str(int(float_value)) + ".\n", "get")
                    else:
                        response_texts[0].insert(tk.END, "Error! Please try again.\n", "fail")
                else:
                    response_texts[0].insert(tk.END, "No response received.\n")

            if auto_scroll_var.get():
                response_texts[0].see(tk.END)
    except serial.SerialException as e:
        messagebox.showerror("Serial Error", str(e))

def send_custom_command(hex_string, label):
    port = com_port_var.get()
    baud = int(baud_rate_var.get())
    try:
        timeout = float(timeout_var.get())
    except ValueError:
        messagebox.showerror("Invalid Timeout", "Please enter a valid number for timeout.")
        return

    try:
        command_bytes = bytes.fromhex(hex_string)
    except ValueError:
        messagebox.showerror("Invalid Hex", "The hex string is not valid.")
        return

    try:
        with serial.Serial(port, baud, timeout=timeout) as ser:
            ser.write(command_bytes)
            response = ser.read(64)
            if response:            
                response_texts[0].tag_configure("success", foreground="green")
                response_texts[0].tag_configure("Disable", foreground="#A06A19")
                response_texts[0].tag_configure("interrupt", foreground="blue")
                response_texts[0].tag_configure("fail", foreground="red")
                if response == b'\x01\x0C\x01\x00\xCC':
                    response_texts[0].insert(tk.END, "Bridge Enabled.\n", "success")
                elif response == b'\x01\x0D\x01\x00\x8C':
                    response_texts[0].insert(tk.END, "Bridge Disabled.\n", "Disable")
                elif response == b'\x01\x05\x01\x00\x56':
                    response_texts[0].insert(tk.END, "Started/Executed.\n", "success")
                elif response == b'\x01\x06\x01\x00\x96':
                    response_texts[0].insert(tk.END, "Stopped.\n", "interrupt")
                elif response == b'\x01\x07\x01\x00\xD6':
                    response_texts[0].insert(tk.END, "Emergency Stop.\n", "interrupt")
                elif response == b'\x01\x03\x01\x00\x60' and label == "UP":
                    response_texts[0].insert(tk.END, "Direction UP.\n", "success")
                elif response == b'\x01\x03\x01\x00\x60' and label == "DOWN":
                    response_texts[0].insert(tk.END, "Direction DOWN.\n", "success")
                elif response == b'\x01\x09\x01\x00\x3A':
                    response_texts[0].insert(tk.END, "RTZ Success.\n", "success")
                elif response == b'\x01\x08\x01\x00\x7A':
                    response_texts[0].insert(tk.END, "Set Zero Success.\n", "success")
                elif response == b'\x01\x10\x01\x00\xA2':
                    response_texts[0].insert(tk.END, "PI Gains have been reset to default.\n", "interrupt")
                elif response == b'\x01\x0E\x01\x00\x4C' and label == "Enable":
                    response_texts[0].insert(tk.END, "Drive to distance Enabled.\n", "success")
                elif response == b'\x01\x0E\x01\x00\x4C' and label == "Disable":
                    response_texts[0].insert(tk.END, "Drive to distance Disabled.\n", "Disable")
                else:
                    response_texts[0].insert(tk.END, "Error! Please try again.\n", "fail")
            else:
                response_texts[0].insert(tk.END, "No response received.\n")
            if auto_scroll_var.get():
                response_texts[0].see(tk.END)
    except serial.SerialException as e:
        messagebox.showerror("Serial Error", str(e))

def clear_resp():
    for text_box in response_texts:
        text_box.delete("1.0", tk.END)

resetPIgains = False
def toggle_gain_fields():
    global resetPIgains
    state = "normal" if enable_gain_fields_var.get() else "disabled"
    for i in range(4, 8):
        float_entries[i].config(state=state)
        send_btn[i].config(state=state)
        get_btn[i].config(state=state)
    rstPIgain_btn.config(state=state)

    if state == "normal":
        response_texts[0].insert(tk.END, "Present PI Gains are:\n")
        send_hex_cmd_frame(GET, SPDKP)
        send_hex_cmd_frame(GET, SPDKI)
        send_hex_cmd_frame(GET, TRQKP)
        send_hex_cmd_frame(GET, TRQKI)
        resetPIgains = True

    if state == "disabled" and resetPIgains:
        resetPIgains = False
        send_custom_command("01 10 00 44", "Reset PI Gains")


root = tk.Tk()
root.title("TCM Test Utility - PN")
root.resizable(False, False)

# base64 STClogo string
logo_base64 = b'''
/9j/4QAYRXhpZgAASUkqAAgAAAAAAAAAAAAAAP/sABFEdWNreQABAAQAAABkAAD/4QP8aHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLwA8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/\
PiA8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJBZG9iZSBYTVAgQ29yZSA1LjYtYzA2NyA3OS4xNTc3NDcsIDIwMTUvMDMvMzAtMjM6NDA6NDIgICAgICAgICI+IDxyZGY6UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3lu\
dGF4LW5zIyI+IDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiIHhtbG5zOnhtcE1NPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIiB4bWxuczpzdFJlZj0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL3NUeXBlL1Jlc291cmNlUmVmIyIgeG1sbnM6eG1wPSJodHRwOi8vbnMu\
YWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0idXVpZDo1RDIwODkyNDkzQkZEQjExOTE0QTg1OTBEMzE1MDhDOCIgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDpGRDQ4MDBFNjlFNTMx\
MUU1QTRCMTlGQzc1RjQwQzE5RCIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDpGRDQ4MDBFNTlFNTMxMUU1QTRCMTlGQzc1RjQwQzE5RCIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgQ0MgMjAxNSAoV2luZG93cykiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJ\
RD0ieG1wLmlpZDo2YmMwNzEyNy05ZTczLTdiNDQtYmNmMC0xZWVjZDFhOTAwMGUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6ODhlZjgwZGEtOWZhZi1hNDQ4LWEwZmQtZjJkN2RmYTI2NzkxIi8+IDxkYzp0aXRsZT4gPHJkZjpBbHQ+IDxyZGY6bGkgeG1sOmxhbmc9IngtZGVmYXVsdCI+UHJp\
bnQ8L3JkZjpsaT4gPC9yZGY6QWx0PiA8L2RjOnRpdGxlPiA8L3JkZjpEZXNjcmlwdGlvbj4gPC9yZGY6UkRGPiA8L3g6eG1wbWV0YT4gPD94cGFja2V0IGVuZD0iciI/Pv/tAEhQaG90b3Nob3AgMy4wADhCSU0EBAAAAAAADxwBWgADGyVHHAIAAAIAAgA4QklNBCUAAAAAABD84R+JyLfJeC80YjQH\
WHfr/+4ADkFkb2JlAGTAAAAAAf/bAIQAAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQICAgICAgICAgICAwMDAwMDAwMDAwEBAQEBAQECAQECAgIBAgIDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD/8AAEQgAKgC4AwERAAIR\
AQMRAf/EAMsAAAICAgMBAAAAAAAAAAAAAAgJBwoFBgADCwQBAAMBAQADAQEBAAAAAAAAAAABAgMEBQYIBwkKEAAABgIABAEECgsIDgsAAAACAwQFBgcBCAAREgkTITU2NzFBFDRUFWVmOAphIjJiM2NV1pdYGiNTZBZWF2cZUYGxgkODRUZ2tncYeDpSwnOzREdXt9eYOREAAQICBgcHAQcEAwEAAAAA\
AQACETHwIUFREgNhcYGxwQQFkaHRMhMGB+HxIkJyghQIkiMzNMJjFRf/2gAMAwEAAhEDEQA/AL/HAhBp3ANy4JoPqdbWzU7ElVBhLGNNDIyeownOnNjPOBoYTDUfSMJ48u7yMGVIysCGmbylCjOOgkWcMC+SYBJgJlVfPq0vdzmVwW/deouzs2E+zi55zPNh6dk7wqAUJdM5KsUyW2a1QAN55KSqeZj4\
zpAjyBOWSvKBjAfBBhxxDSN30WmZlhkC2XH60mrp3ErJeZxbH1kDu3xC07LibPsBECmiMWDM4+1lGUZTZwym5mkbk3IixHHww040RaZMHHUMQhZ5eXOc+XiiQCRAT0+K3ZktcwOJMSKWJvvYa79OzO123y/WTdmw43LC7ViCw2lHpDCYRA8tdhRMtU9uEZPFFWhjLcgy+LgVDJwfg0YVbcUWVjGTxYyq\
jrU5mXgAIjBOL78/ctkfbf1BRPlRPTU17HXFL0MMqIbk1tz+UyIWkxM9z6aKGJ2Tqm1wSszEAtCWE8sZYVzqnFkIsBFjgEolQxuN2GxUuP2mLvAfrBw39A9LfmRwYhcO/wAVv6DbzTYnH253nu4ZE+yZqhuix2/HUt/2htRZNZzWVGVVXClvc4XHsWOBoayI0fHBxxvPTDjqUWVBKUBxmAZwIWeoWcur\
DihStZBg9U5cTD6DxScP2mLvAfrBw39A9LfmRwsQuHf4rX0G3mmxc/aYu8B+sHDf0D0t+ZHBiFw7/FHoNvNNiPW+O/V3NoJoboBekbu+LpbJvmS7gt1luptPVWsTvCSpJ7XTFBy07UqipzW05a22QqgjylJJEoybgRuR5AHOGYAAwFazblgvc0kwENyAr9pi7wH6wcN/QPS35kcLELh3+K09Bt5psXP2\
mLvAfrBw39A9LfmRwYhcO/xR6DbzTYmI6Md9ruYXlVncPlFiXdF3R51+0okdx1eYlp+rWr4nnzfatXxpM8nktcXRkuyYlkka0gSZUA9PkSgJmQ9ZYc8U2BsFAVlmZYa5oBNZ4hLu/aYu8B+sHDf0D0t+ZHE4hcO/xWvoNvNNi5+0xd4D9YOG/oHpb8yODELh3+KPQbeabE3nRrvUdxG8e3v3VL+sO5oy\
62frBA6OfaadUlUVs1FRlwmEvkLbJVS5pbI8laX8l1bm8oksC1OaFOIsQwfbCzyYga4C3csnsDXhojA+KXXrn9Yr7tNl7CURXUhviJuEfndyVjD35CnpCnkZyxkks1ZGZ2TAVpYcnUpcnN6wwPigMLEXz6sCDnHPACCQICenxVvymtYXAmICZJ3jfrKVp1xfBtA9uaYRhvZqpdHJqtO61sYi88QTiYpR\
iRLIpB0cmbXdmDFYspKGBQ6lliMcluMhTiClJwYrRgKrVOXlYxidULEU3aS2i70m2dUz7dXY22kZetldxWXvdZ1s30fW8fkeyEtYGVzET4C+Pw9BJUFVR10KCNapbTArnlSnEiRZ+1PGGmwJAIAjT7FGaGtqZEkTpTwZdp7s1fsl2BhUKmVoF2vErOY5S/IVI0MGOSS2JNREoG33zXJMCDlVXUAAujTU\
3mtD4ceI4UrSYLzhWmUDUW9rcMRUVg0nFAyTqeMVqucCEofvZ9vL+sY0fmVcxkBmLnq9Ubb1GZwqUkp3SdRxockyiHLSCzQJlBU6jy5W1kDODkCVcoTn5zgJY8CYuVNdgdipBeWXW9hWLr/bMOsyDOTtCLRqSbNUnj6/w1KB1j8siTsWrJKWJDPAPAJOuR5JVJjcYwYDrKMDkIhB4msHSuwgPbCwr10O\
3burCO4DqPVGy8MynRqpU0YarAjBJuTDYRZzAEpDN4ofgefGwSidP3dEMfISltUpj+WMG44o6JLiILThMwvJC2A9fN2/7XLJ/wBcnnhO8x1rry/8bfyjcsbWtgWBQNsQK04YqcIlZFVzGMTyLKzyVSNW2P8AHHFE/sxyhMLKZQNKaYQXkwvOQhPIHkOeYR+VVgqiA9sLCmVd5ruWKe5rtGy2exp3Zkqi\
AVlDIXXcVdC8JjWtzVsje/2g5GpAmqA4UOVhLliYo7JgxntbciyPpFjoC3ESElnlMLWxd5ilKrEC5vMLKXo1aE05MmWElrE5yYw1GsJAoRqiwHAAIaZUnMCYWPGMhGAWBBznGefCWoIMlYnv/wD5aHRD/jkuP/vLj4s+Sl5XMP8AZNLAkqaxbIXPqvZ5dq0OtaEE8Ljz5HAnvcFitiIPiZ8JKLdACjky\
Y5CzDN6CAZCflPkwnOOYRY555y0kGqa2zGNeIOlFML/rsu5r/KuuP/qZrv8A/EvFY8zT3rL0MmkFeO7GE+d91+3HWtu7Pxqt7Jn+LHuRnKXL6mrpjRNqFvmRqICVtj7FF2tjbRDAkBg8ZCYsZ4y8ZNyMQefDLnVGJiRxKwcxrXFokPAJGH1vGBQWDlaLFQqExCHgXDv0S3EWjLJH8rclYqjwcLBNKFIJ\
UEnJgsgwZkWAZGLIeWRC5okltd61yAA4wuUBfVI4ZD5ts9te3zOJxmXIE1CRpUmRSdhan9KnU/zhtpfuggh1SKyiTsljyHIg4xnOM8uE0kAwvHFPmACWx08FaW7ytYVrB+1Zva6QqvINEHNVRLg3qnGLxNgj69SgHJY6eNCoWNLekUHIxHkgHkoQsgyMOM8ueMcUCSazYdxWLQA4QvG8LywoFL5BX05h\
k9iQkoJVCZXHpbGhrWtC+IwP8cdkjwziVsrmmWNrumC4Iy8jTKCTSTw8wDAIIs4zmDAxC7nAFpBlBN5O74nczMNNMMdqhCMZgxjD/uf6746RCFnIscs1TnOOWc+xxpjfSKw9DJv3JnGum7+yu5HaX70QthXKGrRwKqqGDGk8Up2uqqMTCf5y8CdRuBkBi8Z+Ognga03hBVBNyn6RZBnGDRcOJdPTuWZY\
1mY0NlEb1UnIUHpTilKU41MoIGE0k8gwZJxJgM8wGFGliCMsYc+XGcZxnHGS7J1FTlq+60Qx7DU477PR2RSzX1BPo+otyPRNaYgf3OFhWAw6lITychUjCUDODDiSRkqFKcAyijSjBhMAxCNclLw4tODzL2PqoU1qsrCvFdNCjAqkVQqMqazFCy0hMRFBD2dGbFRRopAAtGUx5ZBE+5glhCAJXTjGMexw\
zGNc1xLvilY1rA3F+d4PXsHhrrKVOFkmc4rE2GPOEiV4NOPwqfVrQgRqXZRg9SYPrUCMF1mCFz5iznISTNKAC3nhJoKt/wDbdj0x1pm1sqjkhsxUkiilWsagZWRPthPSVThlBlOZ74b2Uog1yW4xj3okMDj7YQcZ9M9+e5x7W9v5nOZRH/pZv9vIEI/3HA/fINRbliLzGp0AyILwvof+LvwX1L+Qfy/0\
72PkteOgMd+56jnNBhk8jkub6pxDyvziW5GV/wBua0yBIqAa/wC4Pcu2SuaA0tANpLjPk9gyJO1EH5kBw0bOhMENW9SBwASSHwmiPtRR6s/p6cBJJyEPl6ccfL3IdY94dU5/J6dyXUepP5zPzAxg/dcwBE2mDzBrRFzjA4WNc6EAv7z/ACj8C/xA+I/j7qnyH7o9l9Ab0fpXKOzC30AH5rwA3KyGEkxz\
c/MLMpkYxe8E2lCR9Y/7WJ+mlvQfZuuj3+T1Ff5CZmsKRvQsK3Rv2IamrCiTvMgWA6QCU3IkSHyDAsBxgbqW6Y5BBgkOfsXpnIv6d03I5HMzs3mMzJymsdm5hLn5hAre4kkkuNZrOsr/ADa+4OuZXuL3Fz3Wsnk+V6fkc3zWZnM5blmYOX5dr3lwycln4cvLBDWCcAsV9Wk7j52pW3JGs1hPWU1FbavL\
NFi8rDiwN8Ou8XJsr2ShGcYAKRNLDDgsC7IeWBjUIjTM9CXyeQFYgvB5zIjGJier6JBWwxJqe/ryTnljJPIuGzCTijA5CYUaVNHsBhYw58oRgGHOM49rOOE7zHWtMv8Axt/KNydx3udMTq/qbt3bxRVlwREdlNRqFh1nrkxZfgl3hBaljhZTuvEWAvAFM9gyYkwvHIWRmsyoWc888U+sxWPLuhFh1hKh\
0O1Mlm8W29IaxRIKsk2zJmiRyV5SEjNzFoE1AMep7Kzc4JPKLwwRJvVnleJjADVISyufUYHGZAidC3zHYGk2onu93H2aHd0fa6DxlAQ0RSByCv4NE2VIHoRssXiVQV8xMTUlBzz0lI25CAOc55iGPqGLORiFnLeYujq3KMgQyxrO8o2b/wD+Wh0P+zvLcfL7P7pcmf7mOGfJTSsx/smlgSjdHt1rW0Ev\
Im/6aZYC/TQiJSSGlobIjyiTRvDbJy0gFqjLalc2g73eTlEDJRmDsYxjIsZxnAs8SDBbZjBmCBvTif2pLuJf+nWoP6FXj8/+Hj0b/FZft23nu8FdD7Ju4Fp7z6EQrYW42yCtE4f57ZrEsRV1HTYtGAIYzKVTY3CIaDnF1GUrGnBjJw8nC8Uf23LHPlwzYbxxWLm4XFokPAKvf9cZzjloZjn5c52Bzy9v\
lj+aXnn+1z4R8u1a5HnOpD59T8+lVtr/AMPsb/8Acdr4B5TrHFGf5m6jwVqrvff/AJO7zf7FV3+sDDw2z2Hcsh5h+Yb15TVVWK+U/aFb21GEzSsktXT2H2LHkj8h+M2NU+QmQt0laU7y2+KT8YNRy9sLCoI6weKTkQeeOfPiAYGK7XDE0tNoVg0f1pTuIiGMQa41BAEQxCCD+ZZ5F04znOcB6hT/AJi6\
ceTnny54rHo3+Kw/btvPd4I64B3RNiu5H2ke8Odfcep5hxVNW0qCMYqqFKoeJRmXTlb8a4e8Knx7E4YL/i8n9z5wIHR1GY5Z544oGIjr3LMsGXmNAtI3qphrjEY/YGw1DwOWJDXCLTa5qviMlQEKjkJy2PySbsbM8pCVqfIVCM1S3LTABNBnAy8i6g+XGOIaIuA0rqeSGEiYBTHO9n23Vnbc3MkkKjLa\
qL1+tgLhZOvjkaeoXASxJWvyW81+pcFQz1Kh3rV3P9wCyeaapObTEKo4WRquAi0SU5T8TYHzBPt+q591rKc8rtrXtJDBEqjHV+1Vkr44B8NMd4Z7tKaTyeqFjIS1GQHu0fB1Z/dcrEgc8xoicMVjSKU0allnMgcYkd/1361eG4SxXOBCgG8tcdeL7Ljp1+1xD7BTRYxaVHAzPAzULWofBIy1fuQgatOj\
91rsoiQYFkIjM9OAhzjGc4z691v2p0D3HmZWb1nlxn5mS1wYceY3CHwLh9xzYxwtnGQX6V8e/MXyd8T/ALr/AOcda5zo7ud9P1zyzmsdm+ni9MOdhLoNxuIaCBExIJgteqbT3VGgJWdN6ipKt65mBzOqYzH9haikbphnWnplKxGWeccaIglUajKyYIGAiEEHTnPTzxnDpHsv2x0Lm/3/AErlG5XN4S0O\
xZjyAZwxvcATKIAMCRGBIPl/ff8AIH5q+TeiN9t+/vcvVeq9CbntzhkZ+biy/VYHNY8tAES0PdCMQCYgRgVv93UZSeyteu1T3xXkOtiuXRS1OjrEJi3p3ZnMWNKstzZ3ERIxYMSqUakjBhRwBAHjHVjn0iFjPtIJC/HkDv8AU4dqJIehEHSTXhGrUm9TYYVHsJFZqgoPjBG2mluBZ+VBOMYGEROesHLA\
sZxy58OJmIdgQSZEntK7XHs59qk9bk120n1+Pc3lSpMye4x8Rrk6rjutQrOyoVOIla5caIQjDB9QzRCzkQs8+eeCJNdXYERIqie0oorM1B1Zt+j45rHZ9NwSX0XECYkmi1XO6Y3+L7AVC02G+IAaSSFadajyzog5TkZAbjOSRDLFkQBiDlRM0Sko21+7dWhmotgCsjXzW+qqfsZ5YV8OLk0fSqCXtUxr\
1KFycmhvG6OS3JeFZzYQM7KcITRgKwEQujnjJElBJtJ2lYe0+1l277tsKVWxbeolMz+xpsvLdZZMZLHBLnl9cCUSVvLVr1IlQQjMAiRFF+TGMdIMcETo7AgEiRMNZWVdu3JoJIaWiOuzvrJTznRsElTrPodWShpwbFI/LHgtyw7yJuQ4Wfua1YU7qfEHkWQ9JwvJjHDiaBFsYmOsqJS+zN2ojRdJWjWu\
xgsh6+kuKgGLoz5OrkFbnPTz9v2OFE6OwJxdee0rpJ7N3abUpylafSHXFQkPEIJComMkmpzhAGMsYSjgLxFmCCMsQc4xnPLIc49rgidHYEsTrz2nxRxUPQtJa2V8kqrX6vYrV9ctjm6OqOHw5P7kZUbo+Kcr3VUWnycfks5epH4g/tuWc58mMY4CSZo3qPtidL9S9wDosbsnRlc3cdXuXpLFRTZrw8Cj\
In/DYY+J0WAHl+5huOGtII4IvLnwS8+1jgiQjUSNRWF1+0X0u1BkjxLNdaAq6kJNM2tPEnh2hzaFlWSBsAtA6pmU3xFQwKse7UwTggCHrzkH9jHBEkQsQTeTtKn+1Kwrm6q/k9UW1FWWc13PG4bHKIfICsntEibhDAsG3rE4TChnF9aTBnSEWM48Pn7XADCtCALHZh7U4hDAHRbXrIy+nrBiJYyIHXjO\
QdYcLOYerGPJz9ngidHYE4uvd2ldWezT2oA45i0c11DjrML55ixeMeIT5DgeVb92Vn7rHsh9vgidHYEYnXntPipbhvbZ0ErKv7VqmE6vVDEK6vNvYmy2oe1MwkLNP26LLVDkwJX9NhZgSohoXKjDSsByHpGMWfb4IlI6SY6yo+Y+z/2voo9MktYNKKEZHyMu7XI2J7RRj3MpandmWkObU5pVAVuMFnIl\
yYs0AvY6g49nHDxGNUI6ggkkQJMNZRM7G6pawbZMsfjOzNO11cjNDnU9/jbdPWtO5hYHRaiEhVrUAxGFKEvu1F9qaHAsFm4ADIg5yAGQoRsRKVRQwsnZ97XkdeGqSRzS6i2J/jLs1v7M/MbGoa3ZiemVYmeGh1b3NA5ELG5cgWJijyjQDAIOQ4zjPLh4iLuwIJJqJMNZTJSFqNSnKWJlaZQkP6MEKiDy\
jU53iGYKL8I8sYizOs3OA45ZzzF5PZ4lC7vEL8TJXWDxcAwZkvqD4mC8iyHA8g59XRkQc45+xzxwIVarveNtdPuw2uKexLa1/ZUrDUFruLXRm9hlpV1pvbAnVxbSHR5j1/V4+taSDbNw4hpK+JiFZCk/CRUA9MMg3GMm22oIAJMBGOjbQysSRbFsGsrRtvT6TWQipGvIA+dqqAqojB+5vsXsy1NzWe17\
MXZHG89lsmj25ilFiS1Ywt5eWxa7NqMwyJe5eReDAYyKo104/anhiIT+8ZCO7usRZ2hPbIqW+e4RsVQ7isnmulXaH6VVTcdQVQ+PT3DnvW7YPTyUM0XvOjHuXLsPahVR0/iDWtCpXcliyJrHEw40CjxRcEa64395UgRbCqJq3VHRx2odLkW1q21tRk/tCxqisuS172wtFjh647EWFc+u93N4WSo2V+Is\
Lth39FjXCOzi1rJeFh+XZF8UrFAXkAUyvKggZqXJIUpSaqGImAgI91UxcJ16aijHu5/01nFg9wiQdzKZz2EbDM1bVTIdAWqazCwoxZETqJ4oCNO9aK9bEbO4IU8rvZRdCtwTysSEhUtPfSRgVElIzDyuCRqlGkO+kFIiWggWV/XRCE6u9QfaVO7D7ATm53ayaKil9bDVr2ddO7FtsFzXPalRTOsblUwC\
wFMpl0Pa68Iwie7RUEs5apYlVmtxOHVCArBxeDjeTBNVK4lBwzEsR01QF/FafsnKqjc4xVVxzW8oNsAujvbd1MkbbUm4kxuLWjY14QN0L/jKntPt2XpEHJ7jEnv2ePKs9E8t/wAWr1YXtCEhUYsIMNIyowpr7zo7QmGkkiEDHWLKjoGnTUVcD12umn9mqqc6wJcn5ylcTq2sI1sFVs8XuI7SrtbblSNE\
pTQ603ZOmasKJsti71n3erQmYwJXg0QRFmYyEMEEGOlIViGhVkAaia91OV9YXkVeQd8jj5qXXDjEddViCf2a5q6sj0+04cnCWI4wmeZg4JFSt6cHdUf46wClSWaZjJZgOgvpuJ7fAJgCLYwo4itDBQOdbFGluwRCW9dTaZlki1Fqxsm1raTTfczYXYiHxZdOawVT1x2QrOYuCJKz1s4ri0zfOV8TNC5t\
mF5+SxhThz1OMaUNJpEEOkazaIfSkjJELQlYa4XVr93O6weaop6RtlDUcj2Fi9h6PbIXFNtCEdvoKdsoiMSCoI+qXMztUt2o288amTMxTo5o1ogkjUkhMIAI1RldGlO9BBBiYx0jV27bjUnM9t+LVZqB2g4HsjX1Wy9+lEs0yg+zFuMcNe5XKZ9b1itdDt0hdzmAmSvL4FFKZOclGWQShLITYUnYEEn2\
uIiSQCqIGIgVVnelSdirYhhr7bVwoZ8sCIWZItkabjs3YbArO4kEhqBYhjLUusTDNYrk9YzI7W7hAXGx1jVOC/c7WoSx2PJVWSzABGAu3VilI76koQrlv7LrrjFSnt2bpW573dwk/u6S6SxxrhVU1Ut0FZlsymEVIzVIq+VK57LdWkDE5oWmSbFhuDJqczkFQ8FqQpySysoxKMZkGAEKU7ZJgEy2/XRC\
+qaGjeq776tySU4u1vhm8c/SdrfUqjNijV7gXCTbAZtmZepg1oAjW65xEiZAPDo16xwRZh8QRwh6Wjc387A04erJZ9CIp3Uv1JAC0iswt7R4m7Wjp1Q7hup8W7mu/No2jsBFq3iO1tTdtWc6+tk7ky8gqXtkr1+NGcVEG8zChtLVInR5TJXICcJIgLR48YPV1ZxJbYEVwjC+zek9WIqZHLOqDPZskptJ\
EV/ci7xrY/8A+9fYFqw2gjQNL005YkM9kVZuiOUJD0K1OVhkAE3Cb4ywWWZ9oMWM2TXGkylCcB+EbhSpbhUsLftiG7tM0e3V+wbDN7dYXduZWeMWhdFzw7Xe24vD5ZX7vG5dUljIES+y3mmYm0qw/wAUSnpMoWDFk3B4+flCowMaU4JmREK6rNHdp0rfGuSTywtEaP7bLI0bFzSYWduZuYv2Ep7X6TNk\
psmhaP1es5xSiqqp5fZ06awOdXtdpPsUKROkgdU6pelA4FlljMwAHBbGk7+wakXmqqFlpAsrsida2jEHp3dVj7TNj39WbyHZic7fLtFd/kC2bWOxvEhlGuVQzmLuMPmLbHpkjaWpcvDFmd6NGgLTKBiUY6jBY6+YCYUuPFBABIEocRDuK3O9AsEWnG7UClr/AGFE9OY93Y9OK123Nh7/ADNOTE9PmLUF\
pb48xyV6ZlR8kZapU2MgY0siWpTgLMpsgEadyGYPLJJrt+g48UgBZOH/ACPCWmFqiXYpsot9rfuCVJofYjyzdvdzs/tkxZnltZSSTv1cV7snN9j25gt4WtL8tdD21yKKrRU0rnohrWGtpbpgoGMl5zjHCFeuqWv7FUjEius16qo9/wBkE0LtoWXe0t7p+z1abJNMhQXTrfpJSVDWJJlyhRiNXY6w+5bI\
XxjYqJNwjhp0CC5K2fWR0VE4D1JHMStPjOcF+ST5dFXGnckQBAjTwp32p120Hq8QfRx9LWP6UHq8/wDFe8Pnb8B/v+EyduxS7ZtWDtXzq1fRV9G2/wBavnX/AA3mr5t/B/77im/qnYkdi3dg81TT1Ger2L+YPNXoqt9NP6PfyX8leJwjMTmnZZJRnPvO2t/0QPfrf6fedvwTb9G/+G/B/vPB4Yt81L0j\
ZKly3K3/AFl0f9HL0mU+t/1l/dIfUf8AOb99+z4XCbIz2cUzMSW//wCes79WPogz/wCmv3Lt6d/ND4H9jx+FYJzTtMkP8y9nWn6GPnJL6Zez/k76NPyl+9f4nihb5qXqbvLS5Qtpb9Mzup+avX9Rvnj1s/Rpr/0i/oo/kR+I+MeE7yhUJo0zP/Oj1N/4D8J/o0V66P8AqfJnTwrp0uSvlS9RdWvnCS/R\
K9B3f1a+cPwqX0l+Y/wz7/o4o/qmkNklk6G9Rj59F38PMPUN6jPen+XPx/5Y/FcI+YT4pjy2cFP8P9FI36OeY2v0P9FPeRPo38h/BfxPTxJmmJIYK2/ARH6HvrunXq2/AeaXD0R/pu/Lv8E8Xij+qVNikfpW7Xv59p36Ofp4T69/Pvso/U78/P8Aof4vgbIz2cU3WS2re4178tX1XekKj0a9+ej6D1q/\
OH98+T/C4RsnS5O+SHJV/mx9CHzPGvfX/aF+jHyP+TPvuXF/1KP6Vss18xk/RG9M5/6a+Y/fqf8AA/PP+UH47o4Q/VJM/pmpZbPOlRep/wBGXjzZ508zt3qi+bPwz+B+DwjIzpendKlyxcK9Zso9Rf3El9CvWb6QovSj7z8p/KPh8B8onwQPNZxXzJvPpfqC9dbr728++jefwf8ATX8L+TeDtlTYi2yd\
NqzQvel2epz7hd91709Ei/XZ95+//JPLgunS5F8qXqO4L6gYp9Fjz01egvqB9LSvRT5a+CfK3Twz5vxS2oHls4KaEPrLf/QD0TY/ePrL84Ofn/5p/Af4R43EWWzT/FZxX//Z
'''
# Decode and Load the Image
image_data = base64.b64decode(logo_base64)
# Load Image using PIL
image = Image.open(io.BytesIO(image_data))
photo = ImageTk.PhotoImage(image)
#Dispaly in a Label
logoLabel = tk.Label(root, image=photo)
logoLabel.grid(row=1, rowspan=2, column=4, columnspan=3, padx=(110, 20), pady=(12, 0), sticky="w")

tk.Label(root, text="Select COM Port:").grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="w")
com_port_var = tk.StringVar()
com_ports = list_serial_ports()
com_port_menu = ttk.Combobox(root, textvariable=com_port_var, values=com_ports, state="readonly")
com_port_menu.grid(row=0, column=0, columnspan=2,  padx=(150, 0), pady=10, sticky="w")
if com_ports:
    com_port_var.set(com_ports[0])

tk.Label(root, text="Baud Rate:").grid(row=0, column=2, padx=(30, 0), pady=10, sticky="w")
baud_rate_var = tk.StringVar(value="115200")
baud_rates = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]
baud_menu = ttk.Combobox(root, textvariable=baud_rate_var, values=baud_rates, state="readonly")
baud_menu.grid(row=0, column=3, padx=10, pady=10, sticky="w")

tk.Label(root, text="Timeout (s):").grid(row=0, column=4, columnspan=2,  padx=(30, 10), pady=10, sticky="w")
timeout_var = tk.StringVar(value="0.2")
timeout_entry = ttk.Entry(root, textvariable=timeout_var, width=5)
timeout_entry.grid(row=0, column=5, padx=10, pady=10, sticky="w")

auto_scroll_var = tk.BooleanVar(value=True)
auto_scroll_check = ttk.Checkbutton(root, text="Auto-scroll", variable=auto_scroll_var)
auto_scroll_check.grid(row=2, rowspan=3, column=6, padx=(60, 10), pady=(10, 25), sticky="w")

# Group 1: Bridge Control
system_frame = ttk.LabelFrame(root, text="Bridge Control", padding=(10, 5))
system_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

for label, hex_cmd in [
    ("Enable", "01 0C 00 98"),
    ("Disable", "01 0D 00 18"),
]:
    btn = ttk.Button(system_frame, text=label, command=lambda h=hex_cmd, l=label: send_custom_command(h, l), width=15)
    btn.pack(side=tk.LEFT, padx=5, pady=2)

# Group 2: Direction
direction_frame = ttk.LabelFrame(root, text="Direction", padding=(10, 5))
direction_frame.grid(row=1, column=3, columnspan=2, padx=10, pady=5, sticky="w")

for label, hex_cmd in [
    ("UP", "01 03 02 02 01 F0"),
    ("DOWN", "01 03 02 02 00 46"),
]:
    btn = ttk.Button(direction_frame, text=label, command=lambda h=hex_cmd, l=label: send_custom_command(h, l), width=15)
    btn.pack(side=tk.LEFT, padx=5, pady=2)

# Group 3: Drive To Distance
position_frame = ttk.LabelFrame(root, text="Drive To Distance", padding=(10, 5))
position_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")

for label, hex_cmd in [
    ("Enable", "01 0E 02 02 01 E6"),
    ("Disable", "01 0E 02 02 00 50"),
]:
    btn = ttk.Button(position_frame, text=label, command=lambda h=hex_cmd, l=label: send_custom_command(h, l), width=15)
    btn.pack(side=tk.LEFT, padx=5, pady=2)

# Group 4: Homing
position_frame = ttk.LabelFrame(root, text="Homing", padding=(10, 5))
position_frame.grid(row=2, column=3, columnspan=2, padx=10, pady=5, sticky="w")

for label, hex_cmd in [
    ("RTZ", "01 09 00 C2"),
    ("Set Zero", "01 08 00 42"),
]:
    btn = ttk.Button(position_frame, text=label, command=lambda h=hex_cmd, l=label: send_custom_command(h, l), width=15)
    btn.pack(side=tk.LEFT, padx=5, pady=2)

# Group 5: Execution Control
execution_frame = ttk.LabelFrame(root, text="Execution Control", padding=(10, 5))
execution_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="w")

for label, hex_cmd in [
    ("Start/Execute", "01 05 00 1A"),
    ("Stop", "01 06 00 2C"),
    ("Emergency Stop", "01 07 00 AC"),
]:
    btn = ttk.Button(execution_frame, text=label, command=lambda h=hex_cmd, l=label: send_custom_command(h, l), width=15)
    btn.pack(side=tk.LEFT, padx=5, pady=2)

# Standalone: Reset PI Gains
rstPI_frame = tk.Frame(root)
rstPI_frame.grid(row=13, column=0, columnspan=3, pady=15)
rstPIgain_btn = ttk.Button(rstPI_frame, text="Reset PI Gains", command=lambda h="01 10 00 44", l="Reset PI Gains": send_custom_command(h, l))
rstPIgain_btn.pack(side=tk.LEFT, padx=10)

# Standalone: Clear Response
control_frame = tk.Frame(root)
control_frame.grid(row=13, rowspan = 2, column=3, columnspan=4, padx=(100, 0), pady=15)
clear_btn = ttk.Button(control_frame, text="Clear Response", command=clear_resp)
clear_btn.pack(side=tk.LEFT, padx=10)

# Frame to simulate a colored border
border_frame = tk.LabelFrame(root, text="Response", background="#D4E2EE", padx=2, pady=2) 
border_frame.grid(row=2, column=3, rowspan=14, columnspan=4, padx=(100, 10), pady=(50, 0))

# Styled ScrolledText inside the frame
response_box = scrolledtext.ScrolledText(
    border_frame,
    width=40,
    height=20,
    wrap=tk.WORD,
    font=("Arial", 11),
    bg="#F0F2F8",       # Light background
    bd=0,                 # No internal border
    relief=tk.FLAT,       # Flat look
    insertbackground="black",# Cursor color
    padx=10,
    pady=10
)
response_box.pack()

param_labels = ("Speed (mm/min)", "Distance (mm)", "Acceleration (rpm/s)", "Deceleration (rpm/s)", "Speed Kp", "Speed Ki", "Torque Kp", "Torque Ki")

label_vars = []
float_entries = []
response_texts = []
send_btn = []
get_btn = []


for i in range(8):
    label_var = tk.StringVar(value=param_labels[i])
    label_entry = tk.Label(root, textvariable=label_var, width=20, anchor='w')
    label_vars.append(label_var)

    entry = ttk.Entry(root, width=15)
    float_entries.append(entry)

    sendButton = ttk.Button(root, text="Send", command=lambda idx=i: send_hex_cmd_frame(SEND, idx))
    send_btn.append(sendButton)
    getButton = ttk.Button(root, text="Get", command=lambda idx=i: send_hex_cmd_frame(GET, idx))
    get_btn.append(getButton)

    if i < 4:
        if i == 0:
            label_entry.grid(row=i+4, column=0, columnspan=2, padx=(35, 0), pady=(20, 5), sticky="w")
            entry.grid(row=i+4, column=1, padx=(0, 5), pady=(20, 5), sticky="w")
            sendButton.grid(row=i+4, column=2, padx=10, pady=(20, 5))
            getButton.grid(row=i+4, column=2, columnspan=2, padx=(30, 0), pady=(20, 5))
        else:
            label_entry.grid(row=i+4, column=0, columnspan=2, padx=(35, 0), pady=5, sticky="w")
            entry.grid(row=i+4, column=1, padx=(0, 5), pady=5, sticky="w")
            sendButton.grid(row=i+4, column=2, padx=10, pady=5)
            getButton.grid(row=i+4, column=2, columnspan=2, padx=(30, 0), pady=5)
        response_texts.append(response_box)

    else:
        label_entry.grid(row=i+5, column=0, padx=(35, 0), pady=5, sticky="w")
        entry.grid(row=i+5, column=1, padx=(0, 5), pady=5, sticky="w")
        sendButton.grid(row=i+5, column=2, padx=10, pady=5)
        getButton.grid(row=i+5, column=2, columnspan=2, padx=(30, 0), pady=5)
        response_texts.append(response_box)

    # Insert checkbox after 4th field (index 3)
    if i == 3:
        enable_gain_fields_var = tk.BooleanVar(value=False)
        gain_fields_check = ttk.Checkbutton(
            root,
            text="Enable Speed/Torque PI Gains Configuration",
            variable=enable_gain_fields_var,
            command=toggle_gain_fields
        )
        gain_fields_check.grid(row=i+5, column=0, columnspan=2, padx=10, pady=(20, 10), sticky="w")

toggle_gain_fields()  # Initialize PI field state

root.mainloop()

import math
import psutil
import asyncio
import qrcode
import os
import signal
import sys
import subprocess
import time
import requests
from gpiozero import Button
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags as CharFlags
from bluez_peripheral.util import get_message_bus, Adapter
from bluez_peripheral.advert import Advertisement
from dbus_next import introspection as intr
import json
import mysql.connector

last_press_time = 0
DOUBLE_CLICK_THRESHOLD = 0.4
activation_event = asyncio.Event()
main_loop = None

def update_dashboard_api(action, text):
    try:
        url = "http://127.0.0.1:5001/api/trigger"
        if action == "status":
            requests.post(url, json={"action": "status", "message": text}, timeout=0.5)
        elif action == "message":
            requests.post(url, json={"action": "message", "text": text}, timeout=0.5)
    except Exception as e:
        print(f"Dashboard update failed: {e}")

MANUAL_INTRO = intr.Node.parse("""
<node>
  <interface name="org.bluez.Adapter1">
    <method name="StartDiscovery"></method>
    <method name="StopDiscovery"></method>
    <property name="Powered" type="b" access="readwrite"></property>
    <property name="Address" type="s" access="read"></property>
    <property name="Alias" type="s" access="readwrite"></property>
  </interface>
  <interface name="org.bluez.GattManager1">
    <method name="RegisterApplication"><arg name="application" type="o" direction="in"/><arg name="options" type="a{sv}" direction="in"/></method>
    <method name="UnregisterApplication"><arg name="application" type="o" direction="in"/></method>
  </interface>
  <interface name="org.bluez.LEAdvertisingManager1">
    <method name="RegisterAdvertisement"><arg name="advertisement" type="o" direction="in"/><arg name="options" type="a{sv}" direction="in"/></method>
    <method name="UnregisterAdvertisement"><arg name="service" type="o" direction="in"/></method>
  </interface>
  <interface name="org.freedesktop.DBus.Properties"></interface>
</node>
""")

class PiService(Service):
    def __init__(self):
        super().__init__("0000beef-0000-1000-8000-00805f9b34fb", True)
        self.bt_lock = asyncio.Lock()
        self.phone_connected = False

    @characteristic("0000bef1-0000-1000-8000-00805f9b34fb", 
                    CharFlags.WRITE | CharFlags.NOTIFY | CharFlags.READ)
    def on_write_setting(self, options):
        return bytes("Ready", "utf-8")

    def get_schedule_data(self):
        try:
            print("getting Schedule data")
            db = mysql.connector.connect(
                host="localhost",
                user="remote_user",
                password="pi",
                database="Schedule"
            )
            cursor = db.cursor(dictionary=True)
            
            query = """
                SELECT 
                    id, 
                    task_name, 
                    DATE_FORMAT(task_date, '%Y-%m-%d') as task_date, 
                    DATE_FORMAT(start_time, '%H:%i') as start_time, 
                    DATE_FORMAT(end_time, '%H:%i') as end_time,
                    block_number,
                    is_completed
                FROM student_schedule
                WHERE task_name IS NOT NULL
                ORDER BY task_date ASC, start_time ASC
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            print(rows)
            db.close()
            
            return json.dumps(rows)
        except Exception as e:
            print(f"DB Error: {e}")
            return "[]"
    def get_settings_data(self):
        try:
            print("getting Settings data")
            db = mysql.connector.connect(
                host="localhost",
                user="remote_user",
                password="pi",
                database="Schedule"
            )
            cursor = db.cursor(dictionary=True)
            
            query = """
                SELECT 
                    id, 
                    student_name, 
                    current_mode, 
                    support_level, 
                    age_group, 
                    led_brightness, 
                    adhd_type, 
                    DATE_FORMAT(DOB, '%Y-%m-%d') as DOB 
                FROM system_config;
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            print(rows)
            db.close()
            
            return json.dumps(rows)
        except Exception as e:
            print(f"DB Error: {e}")
            return "[]"
    def get_off_data(self):
        try:
            print("getting Off data")
            db = mysql.connector.connect(
                host="localhost",
                user="remote_user",
                password="pi",
                database="Schedule"
            )
            cursor = db.cursor(dictionary=True)
            
            query = """
                SELECT
                    day_type,
                    hour_of_day
                FROM agent_schedule_rules;
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            print(rows)
            db.close()
            
            return json.dumps(rows)
        except Exception as e:
            print(f"DB Error: {e}")
            return "[]"
    async def send_large_data(self, full_string):
        async with self.bt_lock:
            print("Sending data")
            chunk_size = 200
            total_chunks = math.ceil(len(full_string) / chunk_size)
            
        
            self.on_write_setting.changed(bytes(f"SCHED_START:{total_chunks}", "utf-8"))
            await asyncio.sleep(0.1)
            
        
            for i in range(total_chunks):
                start = i * chunk_size
                end = start + chunk_size
                chunk = full_string[start:end]
                self.on_write_setting.changed(bytes(f"SCHED_PART:{chunk}", "utf-8"))
                await asyncio.sleep(0.05) 
                
        
            self.on_write_setting.changed(bytes("SCHED_END", "utf-8"))
    async def send_settings_data(self, full_string):
        async with self.bt_lock:
            print("Sending Setting data")
            chunk_size = 200
            total_chunks = math.ceil(len(full_string) / chunk_size)
            
        
            self.on_write_setting.changed(bytes(f"Set_START:{total_chunks}", "utf-8"))
            await asyncio.sleep(0.1)
            
        
            for i in range(total_chunks):
                start = i * chunk_size
                end = start + chunk_size
                chunk = full_string[start:end]
                self.on_write_setting.changed(bytes(f"Set_PART:{chunk}", "utf-8"))
                await asyncio.sleep(0.05) 
                
        
            self.on_write_setting.changed(bytes("Set_END", "utf-8"))
    async def send_off_data(self, full_string):
        async with self.bt_lock:
            print("Sending Off data")
            chunk_size = 200
            total_chunks = math.ceil(len(full_string) / chunk_size)
            
        
            self.on_write_setting.changed(bytes(f"OFF_START:{total_chunks}", "utf-8"))
            await asyncio.sleep(0.1)
            
        
            for i in range(total_chunks):
                start = i * chunk_size
                end = start + chunk_size
                chunk = full_string[start:end]
                self.on_write_setting.changed(bytes(f"OFF_PART:{chunk}", "utf-8"))
                await asyncio.sleep(0.05) 
                
        
            self.on_write_setting.changed(bytes("OFF_END", "utf-8"))

    @on_write_setting.setter
    def on_write_setting(self, value, options=None):
        try:
        
            cmd = value.decode("utf-8").strip()
            print(f"--- GOT COMMAND: {cmd} ---")
            
            if cmd == "GET_SETTING":
                print("Processing Settings Request...")
                data = self.get_settings_data()
                asyncio.create_task(self.send_settings_data(data))
                
            elif cmd == "GET_SCHED":
                print("Processing Schedule Request...")
                data = self.get_schedule_data()
                asyncio.create_task(self.send_large_data(data))
            
            elif cmd == "GET_OFF":
                print("Processing Off Request...")
                data = self.get_off_data()
                asyncio.create_task(self.send_off_data(data))
                
        except Exception as e:
            print(f"Error in BLE Write Handler: {e}")
    async def stream_stats(self):
        while True:
        
            is_connected = getattr(self.on_write_setting, "_notify", False)
            if is_connected and not self.phone_connected:
                print(">>> Phone Connected! <<<")
                self.phone_connected = True
            elif not is_connected and self.phone_connected:
                print(">>> Phone Disconnected! <<<")
                self.phone_connected = False

        
            print("Reading CPU temperature...")
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read()) / 1000
                
        
            ram = psutil.virtual_memory().percent
            
        
            stats_msg = f"T:{temp:.1f}|R:{ram:.0f}|B:100" 
            
        
            async with self.bt_lock:
                self.on_write_setting.changed(bytes(stats_msg, "utf-8"))
            
            await asyncio.sleep(5)
    async def send_disconnect_notice(self):
        print("Sending 'OFF' notification to phone...")
        try:
        
            self.on_write_setting.changed(bytes("OFF", "utf-8"))
        except Exception as e:
            print(f"Failed to notify phone: {e}")

pi_service = PiService()
advert = None

def on_button_Double_clicked():
    global last_press_time, mac_address
    current_time = time.time()
    
    time_since_last = current_time - last_press_time
    
    if time_since_last < DOUBLE_CLICK_THRESHOLD:
        print("Double-click detected! Sending Dashboard Triggers...")
        
    
        update_dashboard_api("status", "Bluetooth Active")
        
    
        if mac_address:
            update_dashboard_api("message", f"QR_CODE:{mac_address}")
        else:
            print("Warning: MAC Address not yet retrieved.")
            
        last_press_time = 0 
    else:
        print("Button was pressed!")
        last_press_time = current_time

async def shutdown(sig, loop):
    print(f"\nCaught signal {sig.name}. Cleaning up...")
    

    try:
        await pi_service.send_disconnect_notice()
        print("Waiting for packet delivery...")
        await asyncio.sleep(1.5) 
    except Exception as e:
        print(f"Notice failed: {e}")


    if advert:
        print("Stopping Advertisement...")
        try:
            await advert.unregister()
        except:
            pass
    

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    print("Cleanup complete.")

def setup_pi_security():
    print("Configuring Pi Bluetooth Agent...")

    os.system("sudo bluetoothctl agent off || true") 
    os.system("sudo bluetoothctl power on")
    os.system("sudo bluetoothctl discoverable on")
    os.system("sudo bluetoothctl pairable on")

    os.system("sudo bluetoothctl agent NoInputNoOutput")
    os.system("sudo bluetoothctl default-agent")

async def main():
    global advert, main_loop, mac_address
    main_loop = asyncio.get_running_loop()
    


    button = Button(17)
    button.when_pressed = on_button_Double_clicked
    print("Button listener active on GPIO 17.")


    setup_pi_security()
    print("Initializing Bluetooth Bus...")
    bus = await get_message_bus()
    
    try:
        proxy = bus.get_proxy_object("org.bluez", "/org/bluez/hci0", MANUAL_INTRO)
        adapter = Adapter(proxy)
        await adapter.set_powered(True)
        
        mac_address = await adapter.get_address() 
        print(f"Bluetooth Ready! MAC Address: {mac_address}")
    except Exception as e:
        print(f"Bus Initialization Failed: {e}")
        return


    for s in (signal.SIGINT, signal.SIGTERM):
        main_loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(s, main_loop)))


    await pi_service.register(bus, adapter=adapter)
    stats_task = asyncio.create_task(pi_service.stream_stats())


    qr = qrcode.QRCode(box_size=1)
    qr.add_data(mac_address)
    qr.make()
    qr.print_ascii()


    advert = Advertisement("PiProject", ["0000beef-0000-1000-8000-00805f9b34fb"], 0x0340, 0)
    advert.include_tx_power = False 
    await advert.register(bus, adapter)

    print("Advertising started. Waiting for connection...")
    
    try:
    
        await bus.wait_for_disconnect()
    except asyncio.CancelledError:
        print("Service loop cancelled for shutdown.")
        stats_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
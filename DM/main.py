from multiprocessing import Process, Queue, Manager
import threading
import time
import asyncio
import websockets
import ssl
import json
import ws_messages as socket

from LDS import Lds
from gaze import gaze
from VDP import GPIO
from VDP.GPS import VDP_GPS
from VDP.IMU import VDP_IMU
from lib import gData as g

# --------------------------------------------------------------------------------
#  Constants
# --------------------------------------------------------------------------------
DEIVCE_CODE = "adasdafagfas1_Ada_dasgafsadas"
URL = "wss://api.driving.p-e.kr/ws"

# -- Gaze/LDS Configs
GAZE_VIDEO_PATH = 0 #'./videos/4.mp4'
GAZE_HEF_PATH = './gaze/weight/gaze.hef'
GAZE_LABEL_PATH = './gaze/weight/coco.txt'

LDS_MODE = 1  # 0:jpg, 1:mp4, 2:usb cam
LDS_CAM_CH = 2
LDS_VIDEO_PATH = 2 #"./videos/2.mp4"
LDS_HEF_PATH = "./LDS/yolov7.hef"
LDS_LABEL_PATH = "./LDS/labals.txt"

# --------------------------------------------------------------------------------
#  State Management Class
# --------------------------------------------------------------------------------
class DeviceState:
    def __init__(self, device_code):
        self.device_code = device_code
        self.device_id = None
        self.device_status = 0  # 0: idle, 1: running, 2: stopping
        
        self.threading_running = True
        
        self.mileage = 0
        self.mileage_lock = threading.Lock()
        
        self.ws_lock = asyncio.Lock()

        # Task management for state polling
        self.check_state_task = None
        self.check_state_stop_event = None

    def set_mileage(self, mileage):
        with self.mileage_lock:
            self.mileage = mileage

    def get_mileage(self):
        with self.mileage_lock:
            return self.mileage

# --------------------------------------------------------------------------------
#  WebSocket Communication
# --------------------------------------------------------------------------------
async def init_device(device_state, websocket):
    msg_init = socket.get_init_message(device_state.device_code)
    response = await send_msg(websocket, msg_init, device_state)
    if response in ("RECONNECT", "TIMEOUT", None):
        # Retry once
        websocket = await connect_until_success(URL)
        response = await send_msg(websocket, msg_init, device_state)

    if response not in ("RECONNECT", "TIMEOUT", None):
        try:
            data = json.loads(response)
            device_state.device_id = data["data"]["deviceId"]
            print("DEVICE_ID", device_state.device_id)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ERROR] Failed to parse device ID from response: {response}, error: {e}")
            return None
    return websocket

async def connect_until_success(uri):
    ssl_context = ssl._create_unverified_context()
    while True:
        try:
            print("[INFO] Trying to connect to WebSocket...")
            websocket = await websockets.connect(uri, ssl=ssl_context)
            print("[SUCCESS] Connected to WebSocket server.")
            return websocket
        except Exception as e:
            print(f"[RETRY] Connection failed: {e}")
            await asyncio.sleep(2)

async def send_msg(websocket, msg, device_state, timeout=3.0):
    try:
        async with device_state.ws_lock:
            await websocket.send(json.dumps(msg))
            print(f"[INFO] Message sent: {msg}")

        response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
        print(f"[WS] Response received: {response}")
        return response
    except asyncio.TimeoutError:
        print("[ERROR] WebSocket recv timeout.")
        return "TIMEOUT"
    except websockets.ConnectionClosed:
        print("[ERROR] WebSocket connection closed.")
        return "RECONNECT"
    except Exception as e:
        print(f"[ERROR] Communication failed: {e}")
        return None

async def send_result(websocket, msg_gaze, msg_lds, device_state):
    final_msg = socket.get_stop_message(device_state.device_id, msg_gaze, msg_lds)
    print(final_msg)
    
    result = await send_msg(websocket, final_msg, device_state)
    if result in ("RECONNECT", "TIMEOUT", None):
        # If sending fails, reconnect and try once more.
        websocket = await connect_until_success(URL)
        await send_msg(websocket, final_msg, device_state)

# --------------------------------------------------------------------------------
#  Device State Polling
# --------------------------------------------------------------------------------
async def thread_check_state(websocket, device_state):
    while not device_state.check_state_stop_event.is_set():
        mileage = device_state.get_mileage()
        msg = socket.get_status_message(device_state.device_id, mileage)

        receive = await send_msg(websocket, msg, device_state)

        if receive in ("RECONNECT", "TIMEOUT", None):
            websocket = await connect_until_success(URL)
            await asyncio.sleep(1)
            continue

        try:
            status_data = json.loads(receive)
            status = status_data.get("data", {}).get("status")
        except (json.JSONDecodeError, AttributeError):
            print(f"[WS] Invalid JSON while parsing status: {receive}")
            status = None

        if status is None:
            print(f"[WARN] status missing in response: {receive}")
        else:
            device_state.device_status = status
            update_led_by_status(status)
        
        await asyncio.sleep(1)

def update_led_by_status(status):
    led_states = {
        0: (1, 0, 0),  # RED
        1: (0, 1, 0),  # YELLOW
        2: (0, 0, 1)   # BLUE
    }
    r, y, b = led_states.get(status, (1, 0, 0)) # Default to RED
    print(f"DEVICE_STATE : {status}")
    GPIO.toggle_LED(GPIO.RED_LED, r)
    GPIO.toggle_LED(GPIO.YELLOW_LED, y)
    GPIO.toggle_LED(GPIO.BLUE_LED, b)

def start_check_state_task(websocket, device_state):
    if device_state.check_state_task is None or device_state.check_state_task.done():
        device_state.check_state_stop_event = asyncio.Event()
        device_state.check_state_task = asyncio.create_task(thread_check_state(websocket, device_state))
        print("[INFO] check_state Thread begin")

async def stop_check_state_task(device_state):
    if device_state.check_state_stop_event:
        device_state.check_state_stop_event.set()
    if device_state.check_state_task:
        try:
            await asyncio.wait_for(device_state.check_state_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("[WARN] check_state task did not exit in time.")
        device_state.check_state_task = None
    print("[INFO] check_state Thread end")

# --------------------------------------------------------------------------------
#  Hardware Threads & Multiprocessing
# --------------------------------------------------------------------------------
def VDP_data_init(VDP_data):
    VDP_data.GPS_speed_kph = 0.0
    VDP_data.GPS_total_milg = 0.0
    VDP_data.IMU_tSignalSt = 0

def init_processes_and_threads(gps, imu, VDP_data, gaze_queue, lds_queue, device_state):
    device_state.threading_running = True
    print("INIT THREAD")
    
    gps_thread = threading.Thread(target=thread_GPS, args=(gps, VDP_data, device_state))
    imu_thread = threading.Thread(target=thread_IMU, args=(imu, VDP_data, device_state))

    proc_GAZE = Process(target=gaze.gaze_Run, args=(GAZE_VIDEO_PATH, GAZE_HEF_PATH, GAZE_LABEL_PATH, gaze_queue))
    proc_LDS = Process(target=Lds.Lds_Run, args=(LDS_MODE, LDS_VIDEO_PATH, LDS_HEF_PATH, LDS_LABEL_PATH, lds_queue, VDP_data))

    gps_thread.start()
    imu_thread.start()
    proc_GAZE.start()
    proc_LDS.start()

    return proc_GAZE, proc_LDS, gps_thread, imu_thread

def thread_GPS(gps, VDP_data, device_state):
    gps.initData()
    VDP_data_init(VDP_data)

    while device_state.threading_running:
        result = gps.run()
        if result:
            speed, dist = result
            VDP_data.GPS_speed_kph = round(speed, 1)
            VDP_data.GPS_total_milg = round(dist / 1000.0, 1)
            device_state.set_mileage(VDP_data.GPS_total_milg)
            print(f"speed: {VDP_data.GPS_speed_kph}, mileage: {VDP_data.GPS_total_milg}")
        time.sleep(0.1)

def thread_IMU(imu, VDP_data, device_state):
    while device_state.threading_running:
        tSignal = imu.run()
        if tSignal is not None:
            VDP_data.IMU_tSignalSt = tSignal
        time.sleep(0.05)

def exit_processes_and_threads(gaze_queue, lds_queue, processes, threads, device_state):
    print("EXIT THREAD")
    device_state.threading_running = False
    
    gaze_queue.put("EXIT")
    lds_queue.put("EXIT")
    
    for p in processes:
        p.join()
    for t in threads:
        t.join()

    device_state.set_mileage(0)

# --------------------------------------------------------------------------------
#  Main Application Logic
# --------------------------------------------------------------------------------
async def main():
    # --- Initialization ---
    manager = Manager()
    VDP_data = manager.Namespace()
    device_state = DeviceState(DEIVCE_CODE)
    
    gps = VDP_GPS()
    imu = VDP_IMU()
    gaze_queue = Queue()
    lds_queue = Queue()

    VDP_data_init(VDP_data)
    gps.init()
    imu.init()

    websocket = await connect_until_success(URL)
    websocket = await init_device(device_state, websocket)
    if not websocket or not device_state.device_id:
        print("[FATAL] Could not initialize device with server. Exiting.")
        return

    start_check_state_task(websocket, device_state)

    processes = []
    threads = []
    is_driving = False

    # --- Main Loop ---
    while True:
        await asyncio.sleep(0.1)

        if device_state.device_status == 1 and not is_driving:
            is_driving = True
            print("[INFO] DEVICE_STATE ON")
            proc_GAZE, proc_LDS, gps_thread, imu_thread = init_processes_and_threads(
                gps, imu, VDP_data, gaze_queue, lds_queue, device_state
            )
            processes = [proc_GAZE, proc_LDS]
            threads = [gps_thread, imu_thread]

        elif device_state.device_status == 2 and is_driving:
            is_driving = False
            print("[INFO] DEVICE_STATE OFF")
            
            await stop_check_state_task(device_state)
            exit_processes_and_threads(gaze_queue, lds_queue, processes, threads, device_state)

            raw_msg_gaze = gaze_queue.get() if not gaze_queue.empty() else {}
            msg_gaze = raw_msg_gaze if isinstance(raw_msg_gaze, dict) else {}

            raw_msg_lds = lds_queue.get() if not lds_queue.empty() else {}
            msg_lds = raw_msg_lds if isinstance(raw_msg_lds, dict) else {}
            
            await send_result(websocket, msg_gaze, msg_lds, device_state)
            start_check_state_task(websocket, device_state)
        
        # Add a small delay for other states to prevent busy-waiting
        elif device_state.device_status == 0:
            time.sleep(1)


if __name__ == "__main__":
    GPIO.init_GPIO()
    try:
        asyncio.run(main())
    finally:
        GPIO.exit_GPIO()
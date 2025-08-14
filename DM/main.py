from multiprocessing import Process, Queue, Manager
import threading
import time
import asyncio
import websockets
import ssl
import json

from LDS import Lds
from app import app
from VDP import GPIO
from VDP.GPS import VDP_GPS
from VDP.IMU import VDP_IMU
import gData as g


# --------------------------------------------------------------------------------
#  Flag
# --------------------------------------------------------------------------------
DEVICE_STATE = 0
THREAD_RUN_ST = True
DEIVCE_CODE = "adasdafagfas1_Ada_dasgafsadas"
DEIVCE_ID = None

# --------------------------------------------------------------------------------
#  APP LDS
# --------------------------------------------------------------------------------
APP_CAM_CH = 0

APP_VIDEO_PATH = 0#'./videos/4.mp4'
APP_HEF_PATH = './app/weight/gaze.hef'
APP_LABEL_PATH = './app/weight/coco.txt'


LDS_MODE = 1      # 0:jpg, 1:mp4, 2:usb cam
LDS_CAM_CH = 2

LDS_VIDEO_PATH = 2#"./videos/2.mp4"
LDS_HEF_PATH = "./LDS/yolov7.hef"
LDS_LABEL_PATH = "./LDS/labals.txt"

# --------------------------------------------------------------------------------
#  socket
# --------------------------------------------------------------------------------

URL = "wss://api.driving.p-e.kr/ws"
ssl_context = ssl._create_unverified_context()
ws_lock = asyncio.Lock()
GPS_cur_milg = 0
gps_milg_lock = threading.Lock()

# ------------------------------ WebSocket Utils -------------------------------

async def init_device():
    global DEIVCE_ID
    websocket = await connect_until_success(URL)
    msg_init = {
    "type": "DEVICE:HELLO",
    "payload": {
        "code": DEIVCE_CODE
    }
}
    response = await send_msg(websocket, msg_init)
    if response in ("RECONNECT", "TIMEOUT", None):
        # 한번 더 시도
        websocket = await connect_until_success(URL)
        response = await send_msg(websocket, msg_init)

    data = json.loads(response)
    DEIVCE_ID = data["data"]["deviceId"]
    print("DEVICE_ID", DEIVCE_ID)
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
            print("[RETRY] Connection failed:", e)
            await asyncio.sleep(2)  # 2초 후 재시도


async def send_msg(websocket, msg, timeout=3.0):
    """
    - send 시에만 ws_lock 사용 (recv 지연으로 인한 전체 락 정체 방지)
    - recv 타임아웃을 두고, TIMEOUT 문자열을 반환하여 상위가 복구 처리
    - 연결 종료 시 RECONNECT 반환
    """
    try:
        # SEND 보호
        async with ws_lock:
            await websocket.send(json.dumps(msg))
            print("[INFO] Message sent:", msg)

        # RECV 은 락 없이 (서버 지연으로 다른 송신 막히는 것 방지)
        response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
        print("[WS] Response received:", response)
        return response

    except asyncio.TimeoutError:
        print("[ERROR] WebSocket recv timeout.")
        return "TIMEOUT"

    except websockets.ConnectionClosed:
        print("[ERROR] WebSocket connection closed. Reconnecting needed.")
        return "RECONNECT"

    except Exception as e:
        print("[ERROR] Communication failed:", e)
        return None

# ------------------------------ State Poller ----------------------------------

## 주행상태 확인
async def thread_check_state(websocket, stop_event: asyncio.Event):
    """
    서버에서 상태를 안 돌려주거나 연결이 잠시 끊겨도
    여기서 자체적으로 재연결 및 재시도하여 영속적으로 동작하도록 수정.
    """
    global DEVICE_STATE

    while not stop_event.is_set():
        # mileage 스냅샷
        with gps_milg_lock:
            mileage = GPS_cur_milg

        msg = {
            "type": "DRIVING:STATUS",
            "payload": {
                "deviceId": DEIVCE_ID,
                "mileage": mileage
            }
        }

        receive = await send_msg(websocket, msg)

        # 복구 루틴
        if receive in ("RECONNECT", "TIMEOUT", None):
            # 재연결 시도
            websocket = await connect_until_success(URL)
            await asyncio.sleep(1)
            continue

        # JSON 파싱 보호
        try:
            status = json.loads(receive)
        except Exception as e:
            print("[WS] Invalid JSON while parsing status:", e)
            await asyncio.sleep(1)
            continue

        status = (
            status.get("data", {}).get("status")
            if isinstance(status, dict) else None
        )

        if status is None:
            print("[WARN] status missing in response:", status)
            await asyncio.sleep(1)
            continue

        if status == 0:
            DEVICE_STATE = 0
            print("DEVICE_STATE : 0")
            GPIO.toggle_LED(GPIO.RED_LED, 1)
            GPIO.toggle_LED(GPIO.YELLOW_LED, 0)
            GPIO.toggle_LED(GPIO.BLUE_LED, 0)
        elif status == 1:
            DEVICE_STATE = 1
            print("DEVICE_STATE : 1")
            GPIO.toggle_LED(GPIO.RED_LED, 0)
            GPIO.toggle_LED(GPIO.YELLOW_LED, 1)
            GPIO.toggle_LED(GPIO.BLUE_LED, 0)
        elif status == 2:
            DEVICE_STATE = 2
            print("DEVICE_STATE : 2")
            GPIO.toggle_LED(GPIO.RED_LED, 0)
            GPIO.toggle_LED(GPIO.YELLOW_LED, 0)
            GPIO.toggle_LED(GPIO.BLUE_LED, 1)

        await asyncio.sleep(1)


check_state_task = None
check_state_stop_event = None
check_state_running = False


async def thread_check_state_wrapper(websocket, stop_event):
    # wrapper는 이제 내부에서 stop_event-aware한 poller를 실행
    await thread_check_state(websocket, stop_event)


def start_check_state_task(websocket):
    global check_state_task, check_state_stop_event, check_state_running
    check_state_stop_event = asyncio.Event()
    check_state_task = asyncio.create_task(thread_check_state_wrapper(websocket, check_state_stop_event))
    check_state_running = True
    print("[INFO] check_state Thread begin")


async def stop_check_state_task():
    global check_state_task, check_state_stop_event, check_state_running
    if check_state_stop_event:
        check_state_stop_event.set()
    if check_state_task:
        try:
            await asyncio.wait_for(check_state_task, timeout=2.0)
        except asyncio.TimeoutError:
            print("[WARN] check_state task did not exit in time.")
    check_state_running = False
    print("[INFO] check_state Thread end")


async def send_result(websocket, msg_app, msg_lds):
    flag = True
    final_msg = {
        "type": "DRIVING:STOP",
        "payload": {
            "deviceId": DEIVCE_ID,
            "mileage": msg_lds.get("mileage", 0),
            "bias": msg_lds.get("bias", 0),
            "headway": msg_lds.get("headway", 0),
            "left": msg_app.get("left", 0),
            "right": msg_app.get("right", 0),
            "front": msg_app.get("front", 0)
        }
    }
    print(final_msg)

    while True:
        if flag:
            result = await send_msg(websocket, final_msg)
            if result in ("RECONNECT", "TIMEOUT", None):
                websocket = await connect_until_success(URL)
                continue
            else:
                flag = False
        if not flag:
            break


# --------------------------------------------------------------------------------
#  Namespace data
# --------------------------------------------------------------------------------

def VDP_data_init(VDP_data):
    VDP_data.GPS_speed_kph = 0.0
    VDP_data.GPS_total_milg = 0.0
    VDP_data.IMU_tSignalSt = 0


# --------------------------------------------------------------------------------
#  [Thread]
# --------------------------------------------------------------------------------

def init_thread_multiprocess(gps=None, imu=None, VDP_data=None, app_queue=None, lds_queue=None, websocket=None):
    global THREAD_RUN_ST

    THREAD_RUN_ST = True
    print("INIT THREAD")
    gps_thread = threading.Thread(target=thread_GPS, args=(gps, VDP_data))
    imu_thread = threading.Thread(target=thread_IMU, args=(imu, VDP_data))

    proc_APP = Process(target=app.app_Run, args=(APP_VIDEO_PATH, APP_HEF_PATH, APP_LABEL_PATH, app_queue))
    proc_LDS = Process(target=Lds.Lds_Run, args=(LDS_MODE, LDS_VIDEO_PATH, LDS_HEF_PATH, LDS_LABEL_PATH, lds_queue, VDP_data))

    gps_thread.start()
    imu_thread.start()
    proc_APP.start()
    proc_LDS.start()

    return proc_APP, proc_LDS, gps_thread, imu_thread


def thread_GPS(gps, VDP_data):
    global GPS_cur_milg

    gps.initData()
    VDP_data_init(VDP_data)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while THREAD_RUN_ST:
        result = gps.run()
        if result:
            speed, dist = result
            VDP_data.GPS_speed_kph = round(speed, 1)
            VDP_data.GPS_total_milg = round(dist/1000.0, 1)

            with gps_milg_lock:
                GPS_cur_milg = VDP_data.GPS_total_milg

            print(f"speed: {VDP_data.GPS_speed_kph}, mileage: {VDP_data.GPS_total_milg}")

        time.sleep(0.1)


# 별도 비동기 함수로 분리 (현재 미사용)
async def send_ws_with_lock(websocket, msg):
    async with ws_lock:
        await websocket.send(json.dumps(msg))
        print("[GPS] Sent mileage update:", msg)


def thread_IMU(imu, VDP_data):
    while THREAD_RUN_ST:
        tSignal = imu.run()
        if tSignal is not None:
            VDP_data.IMU_tSignalSt = tSignal
        # print(tSignal)
        time.sleep(0.05)


def exit_thread_multiprocess(app_queue=None, lds_queue=None, proc_APP=None, proc_LDS=None, gps_thread=None, imu_thread=None):
    global THREAD_RUN_ST, GPS_cur_milg

    print("EXIT THREAD")
    app_queue.put("EXIT")
    lds_queue.put("EXIT")
    proc_APP.join()
    proc_LDS.join()

    THREAD_RUN_ST = False
    gps_thread.join()
    imu_thread.join()

    with gps_milg_lock:
        GPS_cur_milg = 0


# --------------------------------------------------------------------------------
#  main
# --------------------------------------------------------------------------------
async def main():
    global THREAD_RUN_ST, DEVICE_STATE, DEIVCE_ID

    # Create instance
    manager = Manager()
    VDP_data = manager.Namespace()
    gps = VDP_GPS()
    imu = VDP_IMU()
    app_queue = Queue()
    lds_queue = Queue()

    # VDP init
    VDP_data_init(VDP_data)
    gps.init()
    imu.init()

    websocket = await init_device()
    start_check_state_task(websocket)

    proc_APP = proc_LDS = gps_thread = imu_thread = None

    flag = 0
    while True:
        await asyncio.sleep(0.1)

        if DEVICE_STATE == 0:
            time.sleep(1)
            print("main 0")
            continue

        elif DEVICE_STATE == 1 and flag == 0:
            flag = 1
            print("[INFO] DEVICE_STATE ON")
            proc_APP, proc_LDS, gps_thread, imu_thread = init_thread_multiprocess(
                gps, imu, VDP_data, app_queue, lds_queue, websocket
            )

        elif DEVICE_STATE == 2 and flag == 1:
            flag = 0
            print("[INFO] DEVICE_STATE OFF")
            exit_thread_multiprocess(
                app_queue, lds_queue, proc_APP, proc_LDS, gps_thread, imu_thread)

            # 종료 시점에 app/lds 결과 수신 시도
            if not app_queue.empty():
                msg_app = app_queue.get()
            else:
                print("[APP] No msg received.")
                msg_app = {}

            if not lds_queue.empty():
                msg_lds = lds_queue.get()
            else:
                print("[LDS] No msg received.")
                msg_lds = {}
            await stop_check_state_task()
            await send_result(websocket, msg_app, msg_lds)
            start_check_state_task(websocket)
        else:
            time.sleep(1)


if __name__ == "__main__":
    #gpio init
    GPIO.init_GPIO()
    asyncio.run(main())
    GPIO.exit_GPIO()

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


MODE = 1      # 0:jpg, 1:mp4, 2:usb cam

DEVICE_STATE = False 
# --------------------------------------------------------------------------------
#  APP
# --------------------------------------------------------------------------------
APP_CAM_CH = 2

## 테스트 버전이라 얼굴 나온 영상 뺌 ㅎㅎ
APP_VIDEO_PATH = './videos/4.mp4'
APP_HEF_PATH = './app/weight/gaze.hef'
APP_LABEL_PATH = './app/weight/coco.txt'


# --------------------------------------------------------------------------------
#  LDS
# --------------------------------------------------------------------------------
LDS_CAM_CH = 0

LDS_VIDEO_PATH = "./videos/2.mp4"
LDS_HEF_PATH = "./LDS/yolov7.hef"
LDS_LABEL_PATH = "./LDS/labals.txt"


# --------------------------------------------------------------------------------
#  socket
# --------------------------------------------------------------------------------
async def send_result(websocket, msg_app, msg_lds) :
    app_flag = True
    Lds_flag = True
    while True :
        if app_flag :
            result = await send_msg(websocket, msg_app)
            if result == "RECONNECT":
                websocket = await connect_until_success(URL)
                continue
            else :
                app_flag = False
        
        if Lds_flag :                
            result = await send_msg(websocket, msg_lds)
            if result == "RECONNECT":
                websocket = await connect_until_success(URL)
                continue
            else :
                Lds_flag = False
            
        if not app_flag and not Lds_flag:
            break
        
        

## 07.31 url 주소 니오면 안될 것 같아서 일단 지움
URL = "wss://api.driving.p-e.kr/ws"
ssl_context = ssl._create_unverified_context()
# --------------------------------------------------------------------------------
#  Thread run state
# --------------------------------------------------------------------------------

THREAD_RUN_ST = True


# --------------------------------------------------------------------------------
#  Namespace data
# --------------------------------------------------------------------------------
def VDP_data_init( VDP_data ):
    VDP_data.GPS_speed_kph = 0.0
    VDP_data.GPS_total_dist = 0.0
    VDP_data.IMU_tSignalSt = 0


# --------------------------------------------------------------------------------
#  [Thread]
# --------------------------------------------------------------------------------
def init_thread_multiprocess(gps = None, imu = None, VDP_data = None, app_queue = None, lds_queue = None) : 
    global THREAD_RUN_ST
    THREAD_RUN_ST = True
    print("INIT THREAD")
    gps_thread = threading.Thread(target=thread_GPS, args=(gps, VDP_data))
    imu_thread = threading.Thread(target=thread_IMU, args=(imu, VDP_data))  

    proc_APP = Process(target=app.app_Run, args=(APP_VIDEO_PATH, APP_HEF_PATH, APP_LABEL_PATH, app_queue))
    proc_LDS = Process(target=Lds.Lds_Run, args=(MODE, LDS_VIDEO_PATH, LDS_HEF_PATH, LDS_LABEL_PATH, lds_queue, VDP_data))

    gps_thread.start()
    imu_thread.start()
    proc_APP.start()
    proc_LDS.start()
    
    # 파란색 led on 
    GPIO.toggle_LED(GPIO.BLUE_LED, 1)
    return proc_APP, proc_LDS, gps_thread, imu_thread
     

def exit_thread_multiprocess(app_queue = None, lds_queue = None, proc_APP = None, proc_LDS = None, gps_thread = None, imu_thread = None):
    global THREAD_RUN_ST
    print("EXIT THREAD")
    app_queue.put("EXIT")
    lds_queue.put("EXIT")
    proc_APP.join()
    proc_LDS.join()

    THREAD_RUN_ST = False
    gps_thread.join()
    imu_thread.join()
    # 파란색 led off 
    GPIO.toggle_LED(GPIO.BLUE_LED, 0)
        
def thread_GPS( gps, VDP_data ):
    while THREAD_RUN_ST:
        result = gps.run()
        if result:
            speed, dist = result
            VDP_data.GPS_speed_kph = speed
            VDP_data.GPS_total_dist = dist
        #print(f"speed: {speed:.1f}, distance: {dist:.1f}")
        time.sleep(0.1)

def thread_IMU(imu, VDP_data ):
    while THREAD_RUN_ST:
        tSignal = imu.run()
        if tSignal is not None:
            VDP_data.IMU_tSignalSt = tSignal
        # print(tSignal)
        time.sleep(0.05)


# --------------------------------------------------------------------------------
#  백엔드 시작/종료 신호 확인 함수
# --------------------------------------------------------------------------------

async def connect_until_success(uri):
    ssl_context = ssl._create_unverified_context()

    while True:
        try:
            print("[INFO] Trying to connect to WebSocket...")
            websocket = await websockets.connect(uri, ssl=ssl_context)
            print("[SUCCESS] Connected to WebSocket server.")
           # await websocket.close()
            return websocket
        except Exception as e:
            print("[RETRY] Connection failed:", e)
            await asyncio.sleep(2)  # 2초 후 재시도
   

async def send_msg(websocket, msg):
    try:
        await websocket.send(json.dumps(msg))
        print("[INFO] Message sent:", msg)

        response = await websocket.recv()
        print("[WS] Response received:", response)
        return response

    except websockets.exceptions.ConnectionClosed:
        print("[ERROR] WebSocket connection closed. Reconnecting...")
        return "RECONNECT"
        
    except Exception as e:
        print("[ERROR] Communication failed:", e)
        return None
    

async def thread_check_state(websocket) : 
    #await asyncio.sleep(0.1)
    msg = {
        "type": "DRIVING:STATUS",
        "payload": {
            "status": True
        }
    }
    ## 여기에 on/off 신호 처리
    try :
        await websocket.send(json.dumps(msg))
        print("[INFO] Message sent:", msg)
        response = await websocket.recv()
        print("[WS] Response received:", response)
    except Exception as e:
        print("[ERROR] Communication failed:", e)
        return None

check_state_task = None
check_state_stop_event = None
check_state_running = False

async def thread_check_state_wrapper(websocket, stop_event):
    while not stop_event.is_set():
        await thread_check_state(websocket)
        await asyncio.sleep(1.0)

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
        await check_state_task
    check_state_running = False
    print("[INFO] check_state Thread end")
    
# --------------------------------------------------------------------------------
#  main
# --------------------------------------------------------------------------------
async def main():

    global THREAD_RUN_ST

    # Create instance
    manager = Manager()
    VDP_data = manager.Namespace()
    gps = VDP_GPS()
    imu = None
    imu = VDP_IMU()
    app_queue = Queue()
    lds_queue = Queue()
    
    # VDP init
    VDP_data_init(VDP_data)
    gps.init()
    imu.init()

    websocket = await connect_until_success(URL)
    start_check_state_task(websocket)
    ##연결 확인..? 
    while True:
        
        # start signal 수신
        print("Press button 0 to start")
        print("Press button 1 to off")
        
        while True:
            if not GPIO.read_button(GPIO.BTN_0):
                break  
            elif not GPIO.read_button(GPIO.BTN_1):
                exit(1)
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.5)
    

        # start thread and process
        proc_APP, proc_LDS , gps_thread, imu_thread= init_thread_multiprocess(gps, imu, VDP_data, app_queue, lds_queue)

        # end signal 수신 
        print("Press button 0 to stop")
        while True:
            if not GPIO.read_button(GPIO.BTN_0):
                exit_thread_multiprocess(app_queue, lds_queue, proc_APP, proc_LDS, gps_thread, imu_thread)
                break
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.5)
        
        
        # 시선 결과 수신
        if not app_queue.empty():
            msg_app = app_queue.get()
        else:
            print("[APP]No msg received.")
            
        if not lds_queue.empty():
            msg_lds = lds_queue.get()
        else:
            print("[LDS]No msg received.")
            
            
        ## webSocket send
        await send_result(websocket, msg_app, msg_lds)
   
        
            

if __name__ == "__main__":
    #gpio init
    GPIO.init_GPIO()
    asyncio.run(main()) 
    GPIO.exit_GPIO()
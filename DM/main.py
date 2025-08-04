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


MODE = 2      # 0:jpg, 1:mp4, 2:usb cam
RED_LED  = 23
YELLOW_LED = 24
BLUE_LED = 25
BTN_0 = 17
BTN_1 = 22
BTN_2 = 27
# --------------------------------------------------------------------------------
#  APP
# --------------------------------------------------------------------------------

APP_CAM_CH = 2

## 테스트 버전이라 얼굴 나온 영상 뺌 ㅎㅎ
APP_VIDEO_PATH = './videos/4.mp4'

## 테스트 가중치 
APP_HEF_PATH = './app/weight/gaze.hef'
APP_LABEL_PATH = './app/weight/coco.txt'


# --------------------------------------------------------------------------------
#  LDS
# --------------------------------------------------------------------------------

LDS_CAM_CH = 0

LDS_IMAGE_PATH = "./LDS/videos/street2.jpg"
# LDS_IMAGE_PATH = "./LDS/videos/highway.jpg"
LDS_VIDEO_PATH = "./videos/2.mp4"

LDS_HEF_PATH = "./LDS/yolov7.hef"
LDS_LABEL_PATH = "./LDS/labals.txt"


# --------------------------------------------------------------------------------
#  socket
# --------------------------------------------------------------------------------

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
#  [Thread] get GPS data
# --------------------------------------------------------------------------------

def thread_GPS( gps, VDP_data ):
    while THREAD_RUN_ST:
        result = gps.run()
        if result:
            speed, dist = result
            VDP_data.GPS_speed_kph = speed
            VDP_data.GPS_total_dist = dist
        #print(f"speed: {speed:.1f}, distance: {dist:.1f}")
        time.sleep(0.1)


# --------------------------------------------------------------------------------
#  [Thread] get IMU data
# --------------------------------------------------------------------------------

def thread_IMU( imu, VDP_data ):
    while THREAD_RUN_ST:
        tSignal = imu.run()
        if tSignal is not None:
            VDP_data.IMU_tSignalSt = tSignal
        print(tSignal)
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
    except Exception as e:
        print("[ERROR] Communication failed:", e)
    # finally:
    #     await websocket.close()
    #     print("[INFO] WebSocket connection closed.")

# --------------------------------------------------------------------------------
#  
# --------------------------------------------------------------------------------

async def main():

    global THREAD_RUN_ST

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

    websocket = await connect_until_success(URL)

    ##연결 확인..? 
    while True:
        
        # start signal 수신
        print("Press button 0 to start")
        print("Press button 1 to off")

        while True :
            if not GPIO.read_button(BTN_0):
                break
            elif not GPIO.read_button(BTN_1):
                exit(1)
            time.sleep(0.1)
        time.sleep(0.5)

        THREAD_RUN_ST = True
        gps_thread = threading.Thread(target=thread_GPS, args=(gps, VDP_data))
        imu_thread = threading.Thread(target=thread_IMU, args=(imu, VDP_data))  

        proc_APP = Process(target=app.app_Run, args=(APP_VIDEO_PATH, APP_HEF_PATH, APP_LABEL_PATH, app_queue))
        proc_LDS = Process(target=Lds.Lds_Run, args=(MODE, LDS_CAM_CH, LDS_HEF_PATH, LDS_LABEL_PATH, lds_queue, VDP_data))

        gps_thread.start()
        imu_thread.start()
        proc_APP.start()
        proc_LDS.start()
        # 파란색 led on 
        GPIO.toggle_LED(BLUE_LED, 1)

        # end signal 수신 
        print("Press button 0 to stop")
        while True:
            if not GPIO.read_button(BTN_0):
            # user_input = input("Enter 1 to end ")
            # if user_input.strip() == '1':
                app_queue.put("EXIT")
                lds_queue.put("EXIT")
                proc_APP.join()
                proc_LDS.join()

                THREAD_RUN_ST = False
                gps_thread.join()
                imu_thread.join()
                # 파란색 led off 
                GPIO.toggle_LED(BLUE_LED, 0)
                break
            time.sleep(0.1)
        time.sleep(0.5)
        
        # 시선 결과 수신
        if not app_queue.empty():
            msg_app = app_queue.get()
            print("[APP]Received:", msg_app)
            await send_msg(websocket, msg_app)
  
        else:
            print("[APP]No msg received.")
            
        if not lds_queue.empty():
            msg_lds = lds_queue.get()
            print("[LDS]Received:", msg_lds)
            await send_msg(websocket, msg_lds)
        else:
            print("[LDS]No msg received.")
            

if __name__ == "__main__":
    #gpio init
    GPIO.init_GPIO()
    asyncio.run(main()) 
    GPIO.exit_GPIO()
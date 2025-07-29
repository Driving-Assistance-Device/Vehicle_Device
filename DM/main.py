from multiprocessing import Process, Queue
import threading
import time
import asyncio
import websockets

from LDS import Lds
from app import app
from VDP.GPS import VDP_GPS
from VDP.IMU import VDP_IMU
import gData as g


MODE = 1      # 0:jpg, 1:mp4, 2:usb cam


# --------------------------------------------------------------------------------
#  APP
# --------------------------------------------------------------------------------

APP_CAM_CH = 0

## 테스트 버전이라 얼굴 나온 영상 뺌 ㅎㅎ
APP_VIDEO_PATH = './app/videos/4.mp4'

## 테스트 가중치 
APP_HEF_PATH = './app/weight/test.hef'
APP_LABEL_PATH = './app/weight/coco.txt'


# --------------------------------------------------------------------------------
#  LDS
# --------------------------------------------------------------------------------

LDS_CAM_CH = 2

LDS_IMAGE_PATH = "./LDS/videos/street2.jpg"
# LDS_IMAGE_PATH = "./LDS/videos/highway.jpg"
LDS_VIDEO_PATH = "./LDS/videos/1.mp4"

LDS_HEF_PATH = "./LDS/yolov7.hef"
LDS_LABEL_PATH = "./LDS/labals.txt"


# --------------------------------------------------------------------------------
#  socket
# --------------------------------------------------------------------------------

URL = "ws://192.168.1.17:8888"


# --------------------------------------------------------------------------------
#  Thread run state
# --------------------------------------------------------------------------------

THREAD_RUN_ST = True


# --------------------------------------------------------------------------------
#  
# --------------------------------------------------------------------------------

# if MODE == 0:
#     Lds.Lds_Run( 0, LDS_IMAGE_PATH, LDS_HEF_PATH, LDS_LABEL_PATH )

# elif MODE == 1:
#     Lds.Lds_Run( 1, LDS_VIDEO_PATH, LDS_HEF_PATH, LDS_LABEL_PATH )

# elif MODE == 2:
#     # Lds.Lds_Run( 2, LDS_CAM_CH, LDS_HEF_PATH, LDS_LABEL_PATH )
#     app.app_Run( APP_CAM_CH, APP_HEF_PATH, APP_LABEL_PATH )


# --------------------------------------------------------------------------------
#  [Thread] get GPS data
# --------------------------------------------------------------------------------

def thread_GPS( gps ):
    while THREAD_RUN_ST:
        result = gps.run()
        if result:
            speed, dist = result
            g.gps_speed_kph = speed
            g.gps_total_dist = dist
        time.sleep(0.1)


# --------------------------------------------------------------------------------
#  [Thread] get IMU data
# --------------------------------------------------------------------------------

def thread_IMU( imu ):
    while THREAD_RUN_ST:
        tSignal = imu.run()
        if tSignal is not None:
            g.IMU_tSignalSt = tSignal
        time.sleep(0.1)


# --------------------------------------------------------------------------------
#  백엔드 시작/종료 신호 확인 함수
# --------------------------------------------------------------------------------

def check_start_cmd():

    return True


def check_stop_cmd():

    return False

async def connet_socket(URL) :
    try:
        async with websockets.connect(URL):
            print("Connected to server")
            return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

# --------------------------------------------------------------------------------
#  
# --------------------------------------------------------------------------------

def main():

    global THREAD_RUN_ST

    # Create instance
    gps = VDP_GPS()
    imu = VDP_IMU()

    app_queue = Queue()
    lds_queue = Queue()
    
    # VDP init
    gps.init()
    imu.init()




    ##연결 확인..? 
    while True:

        while True :
            connected = connet_socket(URL)
            if connected :
                break
    
        
        # start signal 수신
        while True :
            user_input = input("Enter 1 to start, 2 to exit")
            if user_input.strip() == '1':
                break
            if user_input.strip() == '2':
                exit(1)
            time.sleep(0.2)

        THREAD_RUN_ST = True
        gps_thread = threading.Thread(target=thread_GPS, args=(gps,))
        imu_thread = threading.Thread(target=thread_IMU, args=(imu,))  

        proc_APP = Process(target=app.app_Run, args=(APP_VIDEO_PATH, APP_HEF_PATH, APP_LABEL_PATH, app_queue))
        proc_LDS = Process(target=Lds.Lds_Run, args=(MODE, LDS_VIDEO_PATH, LDS_HEF_PATH, LDS_LABEL_PATH, lds_queue))

        gps_thread.start()
        imu_thread.start()
        proc_APP.start()
        proc_LDS.start()

        # end signal 수신 
        while True:
            user_input = input("Enter 1 to end ")
            if user_input.strip() == '1':
                app_queue.put("EXIT")
                lds_queue.put("EXIT")
                proc_APP.join()
                proc_LDS.join()

                THREAD_RUN_ST = False
                gps_thread.join()
                imu_thread.join()
                break
            time.sleep(0.2)
        
        
        # 시선 결과 수신
        if not app_queue.empty():
            msg = app_queue.get()
            print("[APP]Received:", msg)
  
        else:
            print("[APP]No msg received.")
            
        if not lds_queue.empty():
            msg = lds_queue.get()
            print("[LDS]Received:", msg)
  
        else:
            print("[LDS]No msg received.")
            
                


if __name__ == "__main__":

    main()
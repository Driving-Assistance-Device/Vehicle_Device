from multiprocessing import Process, Queue
import time
import asyncio
import websockets

from LDS import Lds
from app import app


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
    app_queue = Queue()
    lds_queue = Queue()
    
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
            
        proc_APP = Process(target=app.app_Run, args=(APP_VIDEO_PATH, APP_HEF_PATH, APP_LABEL_PATH, app_queue))
        proc_LDS = Process(target=Lds.Lds_Run, args=(MODE, LDS_VIDEO_PATH, LDS_HEF_PATH, LDS_LABEL_PATH, lds_queue))

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
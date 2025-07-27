from multiprocessing import Process
import time

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
LDS_VIDEO_PATH = "./LDS/videos/testVideo_7.MP4"

LDS_HEF_PATH = "./LDS/yolov7.hef"
LDS_LABEL_PATH = "./LDS/labals.txt"


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


# --------------------------------------------------------------------------------
#  
# --------------------------------------------------------------------------------

def main():
    
    ##연결 확인..? 
    while True:
        while not check_start_cmd():
            time.sleep(1)

        
        # start signal 수신
        while True :
            user_input = input("Enter 1 to start ")
            if user_input.strip() == '1':
                break
            time.sleep(0.2)
            
        proc_APP = Process(target=app.app_Run, args=(APP_VIDEO_PATH, APP_HEF_PATH, APP_LABEL_PATH))
        proc_LDS = Process(target=Lds.Lds_Run, args=(MODE, LDS_VIDEO_PATH, LDS_HEF_PATH, LDS_LABEL_PATH))

        proc_APP.start()
        proc_LDS.start()

        # end signal 수신 
        while True:
            user_input = input("Enter 1 to end ")
            if user_input.strip() == '1':
                break
            time.sleep(0.2)

        # 종료 명령 실행
        app.app_setExit()
        Lds.Lds_setExit()

        proc_APP.terminate()
        proc_LDS.terminate()

        proc_APP.join()
        proc_LDS.join()

        print("▶ 모든 프로세스가 종료되었습니다.")
        break  # 한 번 종료 후 루프 탈출


if __name__ == "__main__":

    main()
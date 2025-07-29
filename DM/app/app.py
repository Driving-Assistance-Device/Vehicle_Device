import cv2
import numpy as np
import mediapipe
import time
import app.package.gazeDetection as gaze
import app.package.faceAngle as faceAngle


exit_flag = False



# 시선 추적 알고리즘 흐름도 
# 1. 프레임 일고
# 2. mediapipe로 얼굴 각도 추정
# 3. 정면일 경우 Hailo로 pupil 추적 

# HEF_PATH = './app/weight/jaewon.hef'
# VIDEO_PATH = 2 #'./app/videos/4.mp4'
# LABEL_PATH = './app/weight/coco.txt'

ANGLE_STATE = None
GAZE_STATE = None
FINAL_STATE = None
frame = None

global LEFT, FRONT, RIGHT
LEFT = 0
FRONT = 0
RIGHT = 0

def camera_init(video_path) :
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened() :
        print("Failed to open video source:", video_path)
        return None
    else :
        return cap



# --------------------------------------------------------------------------------
#  APP Run
# --------------------------------------------------------------------------------

def app_Run(VIDEO_PATH, HEF_PATH, LABEL_PATH, queue):
    global exit_flag, LEFT, FRONT, RIGHT
    
    faceAngle.init()

    cap = camera_init(VIDEO_PATH)

    if cap is None:
        exit(1)
    
    while cap.isOpened():

        # 07.29 종료 시그널 받기
        if not queue.empty() :
            msg = queue.get()
            if msg == "EXIT":
                print("[APP] exit signal received")
                break
        ret, frame = cap.read()

        if not ret:
            break
          
        # 각도
        frame, direction = faceAngle.process_frame_with_mediapipe(frame)
        
        if direction == "LEFT" :
            LEFT += 1
        elif direction == "FRONT" :
            FRONT += 1
        elif direction == "RIGHT" :
            RIGHT += 1
        print("LEFT:", LEFT, "FRONT:", FRONT, "RIGHT:", RIGHT)
        
        #if direction :
            #print("Detected direction:", direction)
        out_frame, detection = gaze.detect_gaze(HEF_PATH, frame, LABEL_PATH)
           
        # 시선
        gaze.getData(out_frame,detection)  
        
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        time.sleep(0.05)
    
    ## 07.29 결과 전송
    cv2.destroyAllWindows()
    result_msg = f"LEFT:{LEFT}, FRONT:{FRONT}, RIGHT:{RIGHT}"
    queue.put(result_msg)


if __name__ == "__main__":
    app_Run()
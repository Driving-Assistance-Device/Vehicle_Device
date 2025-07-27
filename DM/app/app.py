import cv2
import numpy as np
import mediapipe
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

# --------------------------------------------------------------------------------
# 종료 요청 함수 (main에서 호출)
# --------------------------------------------------------------------------------

def app_setExit():
    global exit_flag
    exit_flag = True


# --------------------------------------------------------------------------------
# 종료 루틴 함수
# --------------------------------------------------------------------------------

def app_Stop():
    global exit_flag
    print("APP END")
    cv2.destroyAllWindows()
    exit_flag = False



def camera_init(video_path) :
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened() :
        print("Failed to open video source:", video_path)
        return None
    else :
        return cap



def get_faceAngle() :
    print('faceAngle ')


# --------------------------------------------------------------------------------
#  APP Run
# --------------------------------------------------------------------------------

def app_Run(VIDEO_PATH, HEF_PATH, LABEL_PATH):

    global exit_flag 

    faceAngle.init()

    cap = camera_init(VIDEO_PATH)

    if cap is None:
        exit(1)
    
    while cap.isOpened():

        if exit_flag:
            app_Stop()
            break

        ret, frame = cap.read()

        if not ret:
            #print("Failed to read frame")
            break
          
        # 각도
        frame, direction = faceAngle.process_frame_with_mediapipe(frame)
        
        #if direction :
            #print("Detected direction:", direction)
        out_frame, detection = gaze.detect_gaze(HEF_PATH, frame, LABEL_PATH)
           
        # 시선
        gaze.getData(out_frame,detection)  
        
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            app_Stop()
            break


if __name__ == "__main__":
    app_Run()
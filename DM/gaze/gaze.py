import cv2
import time
from .package import gazeDetection as gaze
from .package import faceAngle as faceAngle

# 시선 추적 알고리즘 흐름도 
# 1. 프레임 읽고
# 2. mediapipe로 얼굴 각도 추정
# 3. 정면일 경우 Hailo로 pupil 추적 

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
#  Gaze Run
# --------------------------------------------------------------------------------

def gaze_Run(VIDEO_PATH, HEF_PATH, LABEL_PATH, queue):
    global LEFT, FRONT, RIGHT
    
    faceAngle.init()

    cap = camera_init(VIDEO_PATH)

    if cap is None:
        exit(1)
    
    while cap.isOpened():

        # 07.29 종료 시그널 받기
        if not queue.empty() :
            msg = queue.get()
            if msg == "EXIT":
                print("[GAZE] exit signal received")
                break
        ret, frame = cap.read()

        if not ret:
            break
          
        # 각도
        frame, face_direction = faceAngle.process_frame_with_mediapipe(frame)
        out_frame, detection = gaze.detect_gaze(HEF_PATH, frame, LABEL_PATH)
        if face_direction == "LEFT" :
            LEFT += 1
        elif face_direction == "FRONT" :
            gaze_dir = gaze.analyze_gaze_direction(detection) 
            if gaze_dir == "LEFT":
                LEFT += 1
            elif gaze_dir == "FRONT":
                FRONT += 1
            elif gaze_dir == "RIGHT":
                RIGHT += 1
        elif face_direction == "RIGHT" :
            RIGHT += 1

        # 시선
        # cv2.imshow("Gaze Detection", cv2.resize(out_frame, (0, 0), fx=0.3, fy=0.3))
        cv2.imshow("Gaze Detection", out_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        # time.sleep(0.05)
    
    ## 07.29 결과 전송
    cv2.destroyAllWindows()

    result_msg = {
        "left": LEFT,
        "front": FRONT,
        "right": RIGHT
    }
    queue.put(result_msg)


if __name__ == "__main__":
    gaze_Run()

import cv2
import numpy as np
import queue
import threading
from lib.utils import HailoAsyncInference
from lib.object_detection_utils import ObjectDetectionUtils

_inference_initialized = False
_input_queue = queue.Queue()
_output_queue = queue.Queue()
_det_utils = None
_hailo_infer = None



def init_hailo_inference(hef_path, labels_path, batch_size=1 ):
    global _inference_initialized, _input_queue, _output_queue, _hailo_infer, _det_utils

    if _inference_initialized:
        return

    _det_utils = ObjectDetectionUtils( labels_path )

    _hailo_infer = HailoAsyncInference(
        hef_path,
        _input_queue,
        _output_queue,
        batch_size,
        send_original_frame=True )

    threading.Thread( target=_hailo_infer.run, daemon=True ).start()
    # Initialize the Hailo inference only once
    _inference_initialized = True   

  
def run( frame ):

    global _input_queue, _output_queue, _det_utils

    if not _inference_initialized:
        raise RuntimeError( "Hailo inference not initialized. Call init_hailo_inference() first." )

    # Input pre processing
    input_shape = _hailo_infer.get_input_shape()
    h, w = input_shape[0], input_shape[1]
    preprocessed = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    preprocessed = _det_utils.preprocess(preprocessed, w, h)

    # Run YOLO inference
    _input_queue.put(([frame], [preprocessed]))

    # Output post processing
    original_frame, infer_result = _output_queue.get(timeout=2.0)
    if isinstance(infer_result, list) and len(infer_result) == 1:
        infer_result = infer_result[0]

    # Get detection data
    detections = _det_utils.extract_detections(infer_result)
    
    frame_with_detections = _det_utils.draw_detections(detections, original_frame)

    return frame_with_detections, detections

def getData(frame, detections) :
    height, width, _ = frame.shape
    
    boxes = detections['detection_boxes']
    classes = detections['detection_classes']
    
    #print('boxes : ', boxes)

def detect_gaze(hef_path, frame, label_path = 'coco.txt'):
    init_hailo_inference(hef_path, label_path)
    
    # while cap.isOpened():
    #     ret, frame = cap.read()
    #     if not ret:
    #         print("Failed to read frame")
    #         break
    output_frame, detections = run(frame)
    # print('detection:', detections)
    # cv2.imshow("Gaze Detection", cv2.resize(output_frame, (0, 0), fx=0.3, fy=0.3))
    #cv2.imshow('Gaze Detection', output_frame)
    
    return output_frame, detections

# 07.31 추가 
def analyze_gaze_direction(detections: dict) -> str:
    '''
    Analyze gaze direction based on eye and pupil detection results.

    Args:
        detections (dict): Output from extract_detections(), containing:
            - 'detection_boxes': List of [x1, y1, x2, y2] (normalized bbox coordinates)
            - 'detection_classes': List of class indices (e.g., 0 for eye, 1 for pupil)
            - 'detection_scores': List of confidence scores
            - 'num_detections': Number of total detections

    Returns:
        str: 'left', 'front', 'right', or 'unknown'
    '''
    eye_box = None
    pupil_box = None

    for box, cls in zip(detections['detection_boxes'], detections['detection_classes']):
        if cls == 0:  # assuming 0 is 'eye'
            eye_box = box
        elif cls == 1:  # assuming 1 is 'pupil'
            pupil_box = box

    if eye_box is None or pupil_box is None:
        return 'unknown'

    # Extract center X position of pupil and eye
    eye_x1, _, eye_x2, _ = eye_box
    pupil_x1, _, pupil_x2, _ = pupil_box

    eye_center_x = (eye_x1 + eye_x2) / 2
    pupil_center_x = (pupil_x1 + pupil_x2) / 2

    # Calculate relative position of pupil inside eye
    eye_width = eye_x2 - eye_x1
    relative_x = (pupil_center_x - eye_x1) / eye_width  # 0 to 1
    # 07. 31 테스트 필요
    # print(relative_x)
    if not (0 <= relative_x <= 1):
        return 'unknown'  # Pupil is not inside eye

    if -0.1 <= relative_x <= 0.3:
        return 'LEFT'
    elif relative_x >= 0.8:
        return 'RIGHT'
    elif 0.3 <= relative_x <= 0.8:
        return 'FRONT'

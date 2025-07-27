import cv2
import numpy as np
import queue
import threading
from utils import HailoAsyncInference
from object_detection_utils import ObjectDetectionUtils

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
    #print('detection:', detections)
    cv2.imshow('Gaze Detection', output_frame)
    
    return output_frame, detections
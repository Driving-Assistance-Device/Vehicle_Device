import cv2
import numpy as np
import gData as g
import queue
import threading
from utils import HailoAsyncInference
from object_detection_utils import ObjectDetectionUtils



# --------------------------------------------------------------------------------
#  Init YOLO global data
# --------------------------------------------------------------------------------

_inference_initialized = False
_input_queue = queue.Queue()
_output_queue = queue.Queue()
_det_utils = None
_hailo_infer = None


# --------------------------------------------------------------------------------
#  Init hailo inference
# --------------------------------------------------------------------------------

def init_hailo_inference( hef_path="./LDS/yolov7.hef", labels_path="./LDS/labals.txt", batch_size=1 ):
    
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
    _inference_initialized = True


# --------------------------------------------------------------------------------
#  Run hailo object detection
# --------------------------------------------------------------------------------

def runCarDet( frame ):

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


# --------------------------------------------------------------------------------
#  distance estimation -> meter
# --------------------------------------------------------------------------------

def pixel_to_meter( pixel_distance, a=0.04, b=0.0 ):
    """
    픽셀 거리(px) → 실제 거리(m) 변환

    pixel_distance : 하단 중심 ~ 차량 박스 하단 y축 길이

    공식: distance = a * pixel_distance + b

    기본값 a=0.04는 예시 (예: 100px → 4m)
        a : 1픽셀당 실제 거리(m)
    b는 오프셋 (필요시 보정, 일반적으로 0)
    """
    return a * pixel_distance + b


# --------------------------------------------------------------------------------
#  Get car distance
# --------------------------------------------------------------------------------

def getCarDist( frame, detections, laneArea ):

    height, width = frame.shape[:2]
    closest_px_dist = None

    # Class considered as vehicles
    vehicle_classes = [ 'car', 'bus', 'truck', 'motorbike' ]
    class_names = _det_utils.labels

    # Get detection data
    boxes = detections[ 'detection_boxes' ]
    classes = detections[ 'detection_classes' ]
    scores = detections[ 'detection_scores' ]

    # Filter detected objects
    for idx in range(detections['num_detections']):
        cls_id = classes[idx]
        score = scores[idx]
        if score < 0.5:
            continue

        class_name = class_names[cls_id]
        if class_name not in vehicle_classes:
            continue
        
        # Determine inside lane
        ymin, xmin, ymax, xmax = boxes[idx]
        cx = int((xmin + xmax) / 2)
        cy = int(ymax)

        if cv2.pointPolygonTest( laneArea, (cx, cy), False ) < 0:
            continue

        # y-axis distance from the bottom center of the frame to the box
        pixel_dist = height - cy
        if ( closest_px_dist is None ) or ( pixel_dist < closest_px_dist ):
            closest_px_dist = pixel_dist

    if closest_px_dist is not None:
        g.car_dist = pixel_to_meter( closest_px_dist )
    else:
        g.car_dist = -1  # Exception value without vehicle           # del??




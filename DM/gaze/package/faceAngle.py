import cv2
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh
_face_mesh = None  # 전역 변수로 face_mesh 객체 관리

def init():
    global _face_mesh
    print('mediapipe initialized')

    _face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

def get_face_bbox(landmarks, image_width, image_height):
    x_coords = [landmark.x * image_width for landmark in landmarks]
    y_coords = [landmark.y * image_height for landmark in landmarks]
    
    x_min = int(min(x_coords))
    x_max = int(max(x_coords))
    y_min = int(min(y_coords))
    y_max = int(max(y_coords))
    
    padding_x = int((x_max - x_min) * 0.1)
    padding_y = int((y_max - y_min) * 0.1)
    
    x_min = max(0, x_min - padding_x)
    y_min = max(0, y_min - padding_y)
    x_max = min(image_width, x_max + padding_x)
    y_max = min(image_height, y_max + padding_y)
    
    return x_min, y_min, x_max, y_max

def get_head_direction(landmarks, face_width):
    nose_x = landmarks[1].x
    left_cheek_x = landmarks[234].x
    right_cheek_x = landmarks[454].x

    nose_px = nose_x * face_width
    left_px = left_cheek_x * face_width
    right_px = right_cheek_x * face_width

    face_center = (left_px + right_px) / 2
    diff = nose_px - face_center
    threshold = face_width * 0.08
    
    #print(f"Face width: {face_width}, diff: {diff:.2f}, threshold: {threshold:.2f}")
    # 07.31 1차 테스트
    if diff > 50 :#threshold:
        return "LEFT"
    elif diff < -60 :#-threshold:
        return "RIGHT"
    else:
        return "FRONT"

def process_frame_with_mediapipe(frame):
    """cap.read()로 얻은 frame을 넣으면 시선 방향 추정 결과를 반환합니다."""
    global _face_mesh
    if _face_mesh is None:
        raise RuntimeError("Call mediapipeInit() first.")

    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = _face_mesh.process(rgb)

    direction = None

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            x_min, y_min, x_max, y_max = get_face_bbox(
                face_landmarks.landmark, w, h
            )

            face_width = x_max - x_min
            face_height = y_max - y_min

            if face_width > 0 and face_height > 0:
                adjusted_landmarks = []
                for landmark in face_landmarks.landmark:
                    rel_x = (landmark.x * w - x_min) / face_width
                    rel_y = (landmark.y * h - y_min) / face_height
                    adjusted_landmarks.append(type('obj', (object,), {'x': rel_x, 'y': rel_y}))
                
                direction = get_head_direction(adjusted_landmarks, face_width)
                cv2.putText(frame, direction, (x_min, y_min - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)

    return frame, direction

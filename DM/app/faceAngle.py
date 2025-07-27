import cv2
import mediapipe as mp
import numpy as np

VIDEO_PATH = './videos/4.mp4'
mp_face_mesh = mp.solutions.face_mesh

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
    
    print(f"Face width: {face_width}, diff: {diff:.2f}, threshold: {threshold:.2f}")
    
    if diff > threshold:
        return "Head turned LEFT"
    elif diff < -threshold:
        return "Head turned RIGHT"
    else:
        return "Head facing CENTER"

def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    
    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)

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
                        
                        # 얼굴 위치 상단에 시선 방향 출력
                        cv2.putText(frame, direction, (x_min, y_min - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        
                        # 바운딩 박스도 시각화 (선택사항)
                        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
            
            cv2.imshow("Face Direction Detection", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

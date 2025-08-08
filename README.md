# Dev Environemnt 

## Host Environment 
### Build PC 
- **CPU** : Intel i7 13th
- **GPU** : NVIDIA RTX 4050
- **RAM** : 32GB
- **OS** : Ubuntu-22.04 LTS (WSL2)
- **Target** Hailo NPU : Hailo8  

### Hailo SDK
- **Hailo Model Zoo** : 2.15v
- **DataFlow Compiler** : 3.31v
- **Hailort** : 4.21v
- **Python venv** : 3.10.2


## Target Environemnt
### HW
- **Target Board** : RasberryPI 5
- **NPU** : Hailo 8

### SW
- **Python** : 3.11.4
- **HailoRT** : 4.20v  


# System Overview
<img width="747" height="305" alt="Image" src="https://github.com/user-attachments/assets/e801dcb8-b9e7-4b6f-a118-64af0e3e18f0" />

- **MultiProcessor**
    - To enhance system efficiency and prevent resource bottlenecks, the application uses multiprocessing. Independent processes are assigned to handle gaze tracking (app.py) and lane detection with distance estimation (lds.py), enabling parallel execution of compute-intensive tasks.

- **MultiThread**
    - Multithreading is used for handling GPS and IMU data concurrently. GPS data is used to measure driving distance and speed, while IMU data helps determine the vehicle’s turn signal status (e.g., left or right turn). This approach improves responsiveness and stability of the system.

- **Communication (WebScoket)**
  - the device and server are connected via a TCP-based websocket communication protocol.

- **Hailo NPU**
    - Since the Raspberry Pi lacks a dedicated GPU, the system utilizes the Hailo NPU for efficient and real-time AI model inference on edge device

- **Used  library**
    - *OpenCV* : For lane detection
    - *Mediapipe* : For estimating user's face angle 


- [HUD](https://github.com/Driving-Assistance-Device/HUD)

# Feature
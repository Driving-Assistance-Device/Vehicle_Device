<p align="center">
 <img src="https://github.com/user-attachments/assets/8b9fc36d-1d94-413f-a5f7-c34c76e19fc4" width="550"/>  
</p>


# Dev Environemnt 
## Host Environment 
### Build PC 
- **CPU** : Intel i7 13th
- **GPU** : NVIDIA RTX 4050
- **RAM** : 32GB
- **OS** : Ubuntu-22.04 LTS (WSL2)
- **Target Hailo NPU** : Hailo8  

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
<p align="center">
 <img width="850" alt="Image" src="https://github.com/user-attachments/assets/881b3391-7c48-4911-bc41-1c6551bb9cd7" />
</p>

- **MultiProcessor**
    - To enhance system efficiency and prevent resource bottlenecks, the application uses multiprocessing. Independent processes are assigned to handle gaze tracking (app.py) and lane detection with distance estimation (lds.py), enabling parallel execution of compute-intensive tasks.

- **MultiThread**
    - Multithreading is used for handling GPS and IMU data concurrently. GPS data is used to measure driving distance and speed, while IMU data helps determine the vehicle’s turn signal status (e.g., left or right turn). This approach improves responsiveness and stability of the system.

- **WebScoket**
  - the device and server are connected via a TCP-based websocket communication protocol.

- **Hailo NPU**
    - Since the Raspberry Pi lacks a dedicated GPU, the system utilizes the Hailo NPU for efficient and real-time AI model inference on edge device

- **Used  library**
    - *OpenCV* : For lane detection
    - *Mediapipe* : For estimating user's face angle 


- [HUD](https://github.com/Driving-Assistance-Device/HUD)
    - Lane deviation and inter-vehicle distance data are received from a Raspberry Pi and displayed on an ESP32 module. A combiner-type HUD then projects the information into the driver’s line of sight.


# multi-proess
<img width="800" alt="image" src="https://github.com/user-attachments/assets/8cc2fa3f-8bd0-42fc-9b7c-82005e5e14eb" />

- [main.py](https://github.com/Driving-Assistance-Device/Vehicle_Device/tree/main/DM)
    - Main process
- [lds.py](https://github.com/Driving-Assistance-Device/Vehicle_Device/tree/main/DM/LDS)
    - Lane & inter-vehicle distance detection system
- [gaze.py](https://github.com/Driving-Assistance-Device/Vehicle_Device/tree/main/DM/gaze)  
    - Gaze detection system




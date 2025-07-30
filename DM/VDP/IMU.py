import time
import math
import board
import busio
from adafruit_mpu6050 import MPU6050



# --------------------------------------------------------------------------------
#  IMU (I2C)
# --------------------------------------------------------------------------------

class VDP_IMU:

    def __init__(self):
        self.angleX = 0.0
        self.last_time = 0.0
        self.mpu = None

        self.left_threshold = -15.0
        self.right_threshold = 15.0

        self.IMU_Run = False


    def init(self):
        print("IMU parsing Init")

        i2c = busio.I2C(board.SCL, board.SDA)
        self.mpu = MPU6050(i2c)

        self.angleX = 0.0
        self.last_time = time.time()
        self.IMU_Run = True


    def stop(self):
        print("IMU parsing stop.")
        self.IMU_Run = False


    def getState(self):
        if self.mpu is None:
            return 0

        try:
            a = self.mpu.acceleration
            g = self.mpu.gyro

            now = time.time()
            dt = now - self.last_time
            self.last_time = now

            accel_angle_x = math.atan2(-a[1], math.sqrt(a[0]**2 + a[2]**2)) * 180 / math.pi

            self.angleX = 0.98 * (self.angleX + g[0] * dt) + 0.02 * accel_angle_x 

            # print(f"angleX :{self.angleX}")      #test

            if self.angleX < self.left_threshold:
                return -1
            elif self.angleX > self.right_threshold:
                return 1
            else:
                return 0

        except Exception as e:
            print(f"[IMU] Error: {e}")
            return 0


    def run(self):
        if not self.IMU_Run:
            return None

        tSignal = self.getState()
        return tSignal

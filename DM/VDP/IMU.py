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
        # self.angleX = 0.0
        # self.last_time = 0.0
        self.mpu = None
        self.IMU_Run = False

        # self.left_threshold = -15.0
        # self.right_threshold = 15.0

        self.state = 0
        self.state_start_time = None




    def init(self):
        print("IMU parsing Init")

        i2c = busio.I2C(board.SCL, board.SDA)
        self.mpu = MPU6050(i2c)

        self.IMU_Run = True
        self.state = 0
        self.state_start_time = None 


    def stop(self):
        print("IMU parsing stop.")
        self.IMU_Run = False



    def getState(self):
        if self.mpu is None:
            return 0

        try:
            a = self.mpu.acceleration
            g = self.mpu.gyro


            LEFT_THRESHOLD = -14.0
            RIGHT_THRESHOLD = -31.0
            MARGIN = 5.0
            HOLD_TIME = 0.3

            LEFT_MARGIN = LEFT_THRESHOLD + MARGIN
            RIGHT_MARGIN = RIGHT_THRESHOLD - MARGIN           


            # now = time.time()
            # dt = now - self.last_time
            # self.last_time = now


            print(f"a0:{a[0]:.2f}, a1:{a[1]:.2f}, a2:{a[2]:.2f} | g0:{g[0]:.2f}, g1:{g[1]:.2f}, g2:{g[2]:.2f}")


            roll = math.atan2(a[1], a[2]) * 180 / math.pi  # 좌우 기울기
            print(f"roll: {roll:.2f}")                  # 디버그용

            # roll 기준으로 상태 판단 --------------- [수정]
            if LEFT_MARGIN > roll > LEFT_THRESHOLD:
                return -1   # LEFT
            elif RIGHT_MARGIN < roll < RIGHT_THRESHOLD:
                return 1    # RIGHT
            else:
                return 0    # CENTER



        except Exception as e:
            print(f"[IMU] Error: {e}")
            return 0


    def run(self):
        if not self.IMU_Run:
            return None

        tSignal = self.getState()
        return tSignal

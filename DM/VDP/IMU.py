import math
import board
import busio
from adafruit_mpu6050 import MPU6050



# --------------------------------------------------------------------------------
#  IMU (I2C)
# --------------------------------------------------------------------------------

class VDP_IMU:

    def __init__(self):
        self.mpu = None
        self.IMU_Run = False

        self.state = 0
        self.state_start_time = None

        self._prev_raw_state = 0
        self._stable_count = 0
        self._confirmed_state = 0




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
            MARGIN = 7.0
            COUNT_THRESHOLD = 6  # 약 0.3초 (0.05s * 6)

            LEFT_MARGIN = LEFT_THRESHOLD + MARGIN
            RIGHT_MARGIN = RIGHT_THRESHOLD - MARGIN

            roll = math.atan2(a[1], a[2]) * 180 / math.pi
            # print(f"roll: {roll:.2f}")

            # 1단계: 현재 raw 방향 판별
            if LEFT_MARGIN > roll > LEFT_THRESHOLD:
                raw_state = -1  # LEFT
            elif RIGHT_MARGIN < roll < RIGHT_THRESHOLD:
                raw_state = 1   # RIGHT
            else:
                raw_state = 0   # CENTER

            # 2단계: 연속 유지 확인
            if raw_state == self._prev_raw_state:
                self._stable_count += 1
            else:
                self._stable_count = 1
                self._prev_raw_state = raw_state

            # 3단계: 일정 횟수 유지되면 확정
            if self._stable_count >= COUNT_THRESHOLD:
                if self._confirmed_state != raw_state:
                    self._confirmed_state = raw_state

            return self._confirmed_state

        except Exception as e:
            print(f"[IMU] Error: {e}")
            return self._confirmed_state


    def run(self):
        if not self.IMU_Run:
            return None

        tSignal = self.getState()
        return tSignal

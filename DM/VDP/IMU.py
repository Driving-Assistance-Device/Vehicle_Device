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
        self._prev_raw_state = 0
        self._stable_count = 0
        self._confirmed_state = 0

        self.center = -2.7
        self.sensitivity = 1.0
        self.margin = 5.0

        self.LEFT_THRESHOLD = self.center + self.sensitivity
        self.RIGHT_THRESHOLD = self.center - self.sensitivity
        self.LEFT_MARGIN = self.LEFT_THRESHOLD + self.margin
        self.RIGHT_MARGIN = self.RIGHT_THRESHOLD - self.margin


    def init(self):
        print("IMU parsing Init")

        i2c = busio.I2C(board.SCL, board.SDA)
        self.mpu = MPU6050(i2c)

        self.IMU_Run = True
        self.state = 0


    def stop(self):
        print("IMU parsing stop.")
        self.IMU_Run = False


    def getState(self):
        if self.mpu is None:
            return 0

        try:
            a = self.mpu.acceleration
            g = self.mpu.gyro

            COUNT_THRESHOLD = 4  # (0.05s * 4)


            # roll = math.atan2(a[1], a[2]) * 180 / math.pi

            # print(f"a0:{a[0]:.2f}, a1:{a[1]:.2f}, a2:{a[2]:.2f} | g0:{g[0]:.2f}, g1:{g[1]:.2f}, g2:{g[2]:.2f}")


            if self.LEFT_THRESHOLD < a[1] < self.LEFT_MARGIN:
                raw_state = -1  # LEFT
            elif self.RIGHT_MARGIN < a[1] < self.RIGHT_THRESHOLD:
                raw_state = 1   # RIGHT
            else:
                raw_state = 0   # CENTER

           
            if raw_state == self._prev_raw_state:
                self._stable_count += 1
            else:
                self._stable_count = 1
                self._prev_raw_state = raw_state

            
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

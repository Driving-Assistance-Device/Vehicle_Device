import serial
from math import radians, cos, sin, sqrt, atan2



# --------------------------------------------------------------------------------
# GPS (UART 2)
# --------------------------------------------------------------------------------

class VDP_GPS:
    
    def __init__(self, port = '/dev/ttyAMA2', baudrate = 9600, timeout = 1):

        self.uart = serial.Serial(port, baudrate = baudrate, timeout = timeout)

        self.speed_kph = 0.0        # Speed (km/h)
        self.total_dist = 0.0       # Total distance
        self.prev_lat = None        # Prev latitude
        self.prev_lon = None        # Prev longitude
        self.delta_dist = 0.0       # Distance variation
        
        self.GPS_Run = False


    def calcDist(self, lat1, lon1, lat2, lon2):

        R = 6371000
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c


    def initData(self):
        self.speed_kph = 0.0        # Speed (km/h)
        self.total_dist = 0.0       # Total distance
        self.prev_lat = None        # Prev latitude
        self.prev_lon = None        # Prev longitude
        self.delta_dist = 0.0       # Distance variation        


    def run(self):
        
        if not self.GPS_Run:
            return None

        line = self.uart.readline().decode('ascii', errors = 'ignore').strip()

        if line.startswith('$GPRMC'):
            parts = line.split(',')

            if parts[2] == 'A':
                raw_lat = parts[3]
                raw_lat_dir = parts[4]
                raw_lon = parts[5]
                raw_lon_dir = parts[6]
                speed_knots = float(parts[7]) if parts[7] else 0.0
                self.speed_kph = speed_knots * 1.852

                lat_deg = float(raw_lat[:2])
                lat_min = float(raw_lat[2:])
                lat = lat_deg + lat_min / 60.0
                if raw_lat_dir == 'S':
                    lat = -lat

                lon_deg = float(raw_lon[:3])
                lon_min = float(raw_lon[3:])
                lon = lon_deg + lon_min / 60.0
                if raw_lon_dir == 'W':
                    lon = -lon

                if self.prev_lat is not None and self.prev_lon is not None:
                    self.delta_dist = self.calcDist(self.prev_lat, self.prev_lon, lat, lon)
                    self.total_dist += self.delta_dist
                else:
                    self.delta_dist = 0.0

                self.prev_lat = lat
                self.prev_lon = lon

                return self.speed_kph, self.total_dist
        
        return None


    def getData(self):
        return {
            'speed_kph': self.speed_kph,
            # 'delta_distance': self.delta_dist,
            'total_distance': self.total_dist
        }


    def init(self):
        self.GPS_Run = True
        print("GPS parsing Init")


    def stop(self):
        self.GPS_Run = False
        print("GPS parsing stop.")



import gData as g



# --------------------------------------------------------------------------------
#  Define Threshold
# --------------------------------------------------------------------------------

# DIST THRESHOLD
THRESHOLD_DIST_WARN = 5    # Warning
THRESHOLD_DIST_DANG = 3    # Danger     # 속도 비례로 수정


# --------------------------------------------------------------------------------
#  
# --------------------------------------------------------------------------------

def initHandler():
    g.lane_offset = 0
    g.car_dist = 0
    g.raw_count_loop = 0
    g.raw_avg_lOffset = 0
    g.raw_sum_cDist_0 = 0
    g.raw_sum_cDist_1 = 0
    g.raw_sum_cDist_2 = 0
    g.rtn_lOffset = 0
    g.rtn_cDist = 0
    g.rtn_tMilg = 0


# --------------------------------------------------------------------------------
#  Distribution Calculation
# --------------------------------------------------------------------------------

def calc_distribution( a, b ):
    return sum(abs(x - y) for x, y in zip(a, b))


# --------------------------------------------------------------------------------
#  
# --------------------------------------------------------------------------------

def calc_RtnData():

    # Define distribution
    good_heavy = [0.8, 0.1, 0.1]   # 좋음 쏠림
    expected = [0.6, 0.2, 0.2]     # 정상 분포
    warn_heavy = [0.3, 0.35, 0.35] # 경고/위험 쏠림


    # Ignore
    if g.raw_count_loop < 10:
        g.rtn_lOffset = 0
        g.rtn_cDist = 0
        g.rtn_tMilg = 0
        return


    # Lane offset
    g.rtn_lOffset = int(max(-50, min(50, (g.raw_avg_lOffset / 500) * 50)))


    # Car distance
    actual = [ g.raw_sum_cDist_0 / g.raw_count_loop,
               g.raw_sum_cDist_1 / g.raw_count_loop,
               g.raw_sum_cDist_2 / g.raw_count_loop ]

    distances = [ calc_distribution(actual, good_heavy),
                  calc_distribution(actual, expected),
                  calc_distribution(actual, warn_heavy) ]

    g.rtn_cDist = distances.index(min(distances))


# --------------------------------------------------------------------------------
#  Count LDS data
# --------------------------------------------------------------------------------

def countData( lOffset, cDist ):

    g.raw_count_loop += 1

    g.raw_avg_lOffset += (lOffset - g.raw_avg_lOffset) / g.raw_count_loop

    if cDist == 0:
        g.raw_sum_cDist_0 += 1
    elif cDist == 1:
        g.raw_sum_cDist_1 += 1
    elif cDist == 2:
        g.raw_sum_cDist_2 += 1


# --------------------------------------------------------------------------------
#  Data handler
# --------------------------------------------------------------------------------

def runHandler( VDP_data ):

    '''
    input
        LDS_lane_offset, LDS_car_dist
        gps_speed_kph
        IMU data

    output
        HUD_lane_offset
            입력 LDS_lane_offset 그대로.
            방향지시등 on경우 좌 : -999, 우 : 999
        HUD_car_dist
            0 ~ 2
            0 : 정상 (감지x or 정상거리)
            1 : 주의 (가까움)
            2 : 경고
    '''
    # Lane offset
    HUD_lane_offset = g.lane_offset     # test

    # if VDP_data.GPS_speed_kph <= 10.0:  # ignore offset
    #     HUD_lane_offset = 0
    # else:
    #     HUD_lane_offset = g.lane_offset

    # Turn signal state
    HUD_tSig_st = VDP_data.IMU_tSignalSt

    # Distance alarm
    if 0 < g.car_dist <= THRESHOLD_DIST_DANG:     # 속도 비례로 수정
        HUD_car_dist = 2
    elif THRESHOLD_DIST_DANG < g.car_dist <= THRESHOLD_DIST_WARN:
        HUD_car_dist = 1
    else:
        HUD_car_dist = 0

    # cur mileage
    g.rtn_tMilg = VDP_data.GPS_total_milg

    countData( HUD_lane_offset, HUD_car_dist )

    return HUD_lane_offset, HUD_tSig_st, HUD_car_dist
import cv2
import numpy as np
import gData as g



# --------------------------------------------------------------------------------
#  define
# --------------------------------------------------------------------------------

# Init global data
g_first_frame = 1                       # First frame flag

g_prevLane = None                       # Prev lane data
g_curLane = (0, 0, 0, 0, 0, 0, 0, 0)    # Current lane data

g_lanePosX_L = 0                        # Lane X position left
g_lanePosY_L = 0                        # Lane Y position left
g_lanePosX_R = 0                        # Lane X position right
g_lanePosY_R = 0                        # Lane Y position right

g_lanePosX_Top = 0                      # Lane X position Top
g_lanePosY_Top = 0                      # Lane Y position Top
g_lanePosX_Btm = 0                      # Lane X position Bottom
g_lanePosY_Btm = 0                      # Lane Y position Bottom

g_laneCoord_L = ((0, 0))                # Lane center Coordinate left
g_laneCoord_R = ((0, 0))                # Lane center Coordinate Right
g_laneCoord_C = ((0, 0))                # Lane center Coordinate center

LANE_OFFSET_THRESHOLD = 100 # lane offset # 410 ~ 760


# --------------------------------------------------------------------------------
#  Set region of interest mask
# --------------------------------------------------------------------------------

def setROImask( flag=0 ):
    ROI_Def =  np.array( [[230, 650], [610, 460], [670, 460], [1050, 650]] )

    ROI_Wide = np.array( [  [0, 720], [710, 400], [870, 400], [1280, 720]] )
    
    ROI_Wide2 = np.array( [[70, 600], [470, 390], [810, 390], [1210, 600]] )    # Highway

    ROI_Left = np.array([[70, 600], [470, 390], [595, 390], [595, 600]])
    ROI_Right = np.array([[1210, 600], [810, 390], [685, 390], [685, 600]])

    # ROI_Wide2 = np.array( [[70, 610], [470, 400], [810, 400], [1210, 610]] )
    
    if flag == 0: 
        return ROI_Def
    elif flag == 1: 
        return ROI_Wide
    elif flag == 2: 
        return ROI_Wide2
    elif flag == 4:
        return ROI_Left
    elif flag == 5:
        return ROI_Right


# --------------------------------------------------------------------------------
#  Get slope
# --------------------------------------------------------------------------------

def getSlope( x1, y1, x2, y2 ):
    
    if ( x2 - x1 ) == 0:
        return np.inf

    return ( y2 - y1 ) / ( x2 - x1 )


# --------------------------------------------------------------------------------
#  Highlight detect lain
# --------------------------------------------------------------------------------

def hLightDetLain(img, lines):

    global g_prevLane
    global g_first_frame
    global g_curLane


    y_global_min = img.shape[0]
    y_max = img.shape[0]

    l_slope, r_slope = [], []
    l_lane, r_lane = [], []

    det_slope = 0.5
    alpha = 0.2

    # Classification left/right lanes
    if lines is not None:
        for line in lines:
            for x1,y1,x2,y2 in line:
                slope = getSlope(x1,y1,x2,y2)

                if slope > det_slope:
                    r_slope.append(slope)
                    r_lane.append(line)

                elif slope < -det_slope:
                    l_slope.append(slope)
                    l_lane.append(line)

        y_global_min = min(y1, y2, y_global_min)

    # None lane
    if (len(l_lane) == 0 or len(r_lane) == 0):
        return 1

    # Calc slope, lane coordinate avg
    l_slope_mean = np.mean(l_slope, axis =0)
    r_slope_mean = np.mean(r_slope, axis =0)
    l_mean = np.mean(np.array(l_lane), axis=0)
    r_mean = np.mean(np.array(r_lane), axis=0)

    # Slope zero error
    if ((r_slope_mean == 0) or (l_slope_mean == 0 )):
        print('dividing by zero')
        return 1

    # Suboptimal intercept calculatio (y=mx+b -> b=y-mx)
    l_b = l_mean[0][1] - (l_slope_mean * l_mean[0][0])
    r_b = r_mean[0][1] - (r_slope_mean * r_mean[0][0])

    if np.isnan((y_global_min - l_b)/l_slope_mean) or \
    np.isnan((y_max - l_b)/l_slope_mean) or \
    np.isnan((y_global_min - r_b)/r_slope_mean) or \
    np.isnan((y_max - r_b)/r_slope_mean):
        return 1

    # Calc lane start-end points
    l_x1 = int((y_global_min - l_b)/l_slope_mean)
    l_x2 = int((y_max - l_b)/l_slope_mean)
    r_x1 = int((y_global_min - r_b)/r_slope_mean)
    r_x2 = int((y_max - r_b)/r_slope_mean)

    # Case R | L (Error)
    if l_x1 > r_x1:
        l_x1 = ((l_x1 + r_x1)/2)
        r_x1 = l_x1

        l_y1 = ((l_slope_mean * l_x1 ) + l_b)
        r_y1 = ((r_slope_mean * r_x1 ) + r_b)
        l_y2 = ((l_slope_mean * l_x2 ) + l_b)
        r_y2 = ((r_slope_mean * r_x2 ) + r_b)

    # Case L | R
    else:
        l_y1 = y_global_min
        l_y2 = y_max
        r_y1 = y_global_min
        r_y2 = y_max

    # Create cur frame coordinate arr
    current_frame = np.array([l_x1, l_y1, l_x2, l_y2, r_x1, r_y1, r_x2, r_y2], dtype ="float32")

    # Moving average filter
    if g_first_frame == 1:
        g_curLane = current_frame.astype(int)
        g_first_frame = 0
    else:
        prev_frame = g_prevLane
        g_curLane = (1 - alpha) * prev_frame + alpha * current_frame
        g_curLane = g_curLane.astype(int)

    global g_laneCoord_L
    global g_laneCoord_R
    global g_laneCoord_C

    # Calc lane center coordinate
    div = 2
    g_laneCoord_L = (int((g_curLane[0] + g_curLane[2]) / div), int((g_curLane[1] + g_curLane[3]) / div))
    g_laneCoord_R = (int((g_curLane[4] + g_curLane[6]) / div), int((g_curLane[5] + g_curLane[7]) / div))
    g_laneCoord_C = (int((g_laneCoord_L[0] + g_laneCoord_R[0]) / div), int((g_laneCoord_L[1] + g_laneCoord_R[1]) / div))

    global g_lanePosX_Top, g_lanePosY_Top, g_lanePosX_Btm, g_lanePosY_Btm
    g_lanePosX_Top = int((g_curLane[2]+g_curLane[6])/2)
    g_lanePosY_Top = int((g_curLane[3]+g_curLane[7])/2)
    g_lanePosX_Btm = int((g_curLane[0]+g_curLane[4])/2)
    g_lanePosY_Btm = int((g_curLane[1]+g_curLane[5])/2)

    cv2.line(img, (g_curLane[0], g_curLane[1]), (g_curLane[2], g_curLane[3]), g.GREEN, 5)
    cv2.line(img, (g_curLane[4], g_curLane[5]), (g_curLane[6], g_curLane[7]), g.GREEN, 5)

    g_prevLane = g_curLane


# --------------------------------------------------------------------------------
#  Set hought line
# --------------------------------------------------------------------------------

def setHoughLine( Frame, distRes, anglRes, houghTHold, minLineLen, maxLineGap ):
    
    lanes = cv2.HoughLinesP( Frame, distRes, anglRes, houghTHold, np.array([]), 
                            minLineLength=minLineLen, maxLineGap=maxLineGap )

    laneLayer = np.zeros( ( Frame.shape[0], Frame.shape[1], 3 ), dtype=np.uint8 )

    hLightDetLain( laneLayer, lanes )

    return laneLayer


# --------------------------------------------------------------------------------
#  Run lane detect program
# --------------------------------------------------------------------------------

def ldRun( frame ):

    global g_first_frame

    white_H = 255           # mask white range
    white_L = 135           # ( L:100~200, H:255 ) 
                            # 시내 그늘 : 100 ~


    gBlur_kernel = 1        # Gaussian blur kernel size (1 or 3)
    
    cannyTHold_H = 190      # Canny Edge Detection Threshold   
    cannyTHold_L = 120      # ( 50~150, 100~200 )

    distRes = 2             # Distance Resolution
    anglRes = np.pi/180     # Angular Resolution
    houghTHold = 40         # Voting Threshold
    minLineLen = 25         # Minimum Line Length   50
    maxLineGap = 50        # Maximum Line Gap  150


    # 250615 huf param 수정 전 
    # houghTHold = 50         # Voting Threshold
    # minLineLen = 25         # Minimum Line Length   50
    # maxLineGap = 200        # Maximum Line Gap  150


    # 1. Gray scale + mask white, yellow line
    gray = cv2.cvtColor( frame, cv2.COLOR_BGR2GRAY )
    hsv = cv2.cvtColor( frame, cv2.COLOR_RGB2HSV )

    # Mask yellow line
    yellow_L = np.array( [20, 100, 100], dtype="uint8" )        #!! chk yellow det
    yellow_H = np.array( [30, 255, 255], dtype="uint8" )
    mask_Yellow = cv2.inRange( hsv, yellow_L, yellow_H )

    # Mask white line
    mask_White = cv2.inRange( gray, white_L, white_H )

    # Compose line
    mask_WY = cv2.bitwise_or( mask_White, mask_Yellow )
    mask_Line = cv2.bitwise_and( gray, mask_WY )


    # 2. Gaussian blur
    gBlur = cv2.GaussianBlur( mask_Line, (gBlur_kernel, gBlur_kernel), 0 )


    # 3. Canny edges
    cannyEdge = cv2.Canny( gBlur, cannyTHold_L, cannyTHold_H )


    # 4. ROI
    # roiMask = [ setROImask( flag = 2 ) ]

    # Mask_Black = np.zeros_like(cannyEdge)

    # if len( cannyEdge.shape ) > 2:    # RGB
    #     chCnt = cannyEdge.shape[2]
    #     fillColor = ( 255, ) * chCnt
    # else:                           # Grayscale
    #     fillColor = 255

    # cv2.fillPoly( Mask_Black, roiMask, fillColor )

    # roiFrame = cv2.bitwise_and( cannyEdge, Mask_Black )



    # 4. ROI
    roiMask_L = setROImask(flag=4)   # 좌측 ROI (수정)
    roiMask_R = setROImask(flag=5)   # 우측 ROI (수정)

    Mask_Black = np.zeros_like(cannyEdge)

    if len(cannyEdge.shape) > 2:    # RGB
        chCnt = cannyEdge.shape[2]
        fillColor = (255,) * chCnt
    else:                           # Grayscale
        fillColor = 255

    # 좌/우 ROI 각각 적용 (수정)
    cv2.fillPoly(Mask_Black, [roiMask_L], fillColor)
    cv2.fillPoly(Mask_Black, [roiMask_R], fillColor)

    # ROI 적용된 에지 영상 (수정)
    roiFrame = cv2.bitwise_and(cannyEdge, Mask_Black)



    # 5. Hough
    hLine = setHoughLine( roiFrame, distRes, anglRes, houghTHold, minLineLen, maxLineGap )

    result = cv2.addWeighted( frame, 0.8, hLine, 1, 0 )


    return result, hLine


    #for hough Transform test!

    # lines = cv2.HoughLinesP(roiFrame, rho=distRes, theta=anglRes, threshold=houghTHold,
    #                         minLineLength=minLineLen, maxLineGap=maxLineGap)

    # lineFrame = frame.copy()
    # if lines is not None:
    #     for line in lines:
    #         x1, y1, x2, y2 = line[0]
    #         cv2.line(lineFrame, (x1, y1), (x2, y2), (0, 0, 255), 3)

    # return roiFrame, lineFrame


# --------------------------------------------------------------------------------
#  Get lane area
# --------------------------------------------------------------------------------

def getLaneArea():
    pts = np.array([[g_curLane[0], g_curLane[1]], [g_curLane[2], g_curLane[3]],
                    [g_curLane[6], g_curLane[7]], [g_curLane[4], g_curLane[5]]], np.int32)
    
    pts = pts.reshape((-1, 1, 2))

    return pts


# --------------------------------------------------------------------------------
#  Draw lane center (for debug)
# --------------------------------------------------------------------------------

def drawLaneCenter(image, gap = 20, length=20, thickness=2, color = g.RED, bcolor = g.WHITE):
    global l_cent, r_cent

    l_left = 300
    l_right = 520
    l_cent = int((l_left+l_right)/2)
    cv2.line(image, (g_laneCoord_L[0], g_laneCoord_L[1]+length),
             (g_laneCoord_L[0], g_laneCoord_L[1]-length), color, thickness)

    r_left = 730
    r_right = 950
    r_cent = int((r_left+r_right)/2)
    cv2.line(image, (g_laneCoord_R[0], g_laneCoord_R[1]+length),
             (g_laneCoord_R[0], g_laneCoord_R[1]-length), color, thickness)


# --------------------------------------------------------------------------------
#  Draw sreer offset
# --------------------------------------------------------------------------------

def drawSreerOffset(image, height, whalf, color = g.YELLOW):
    cv2.line(image, (whalf-5, height), (whalf-5, 600), g.WHITE, 2)
    cv2.line(image, (g_lanePosX_Btm-5, height), (g_lanePosX_Btm-5, 600), g.RED, 2)


# --------------------------------------------------------------------------------
#  Detect lane offset
# --------------------------------------------------------------------------------

def ldOffset( frame ):
    height, width = frame.shape[:2]
    whalf = int( width/2 )
    hhalf = int( height/2 )

    mask = np.zeros_like( frame )
    # vertices = [setROImask( flag = 2 )]   # for debug
    roiMask_L = setROImask(flag=4)
    roiMask_R = setROImask(flag=5)
    
    if g_laneCoord_L is None or g_laneCoord_R is None or g_laneCoord_C is None:
        return mask
    
    try:
        pts = getLaneArea()

        if g_laneCoord_C[1] >= hhalf:
            laneOffsetVal = g_laneCoord_C[0] - whalf

            g.lane_offset = laneOffsetVal
            # print( f"Lane Offset: {laneOffsetVal}" )

            # if abs(laneOffsetVal) > LANE_OFFSET_THRESHOLD:
            if g_laneCoord_R[0]-g_laneCoord_L[0] > LANE_OFFSET_THRESHOLD:     # lane offset
                cv2.fillPoly( mask, [pts], g.LIME )
                drawLaneCenter( mask )   # for debug 
                drawSreerOffset( mask, height = height, whalf = whalf )

        # Lane Detection ROI
        # cv2.putText( zeros, 'ROI', (930, 650), font, 0.8, yellow, font_size )
        # cv2.polylines( mask, vertices, True, g.RED )   # for debug ROI
        cv2.polylines(mask, [roiMask_L], True, g.RED)  # 좌
        cv2.polylines(mask, [roiMask_R], True, g.RED)  # 우

    except (IndexError, TypeError):
        pass

    return mask


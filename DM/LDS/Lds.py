#--------------------------------------------------------------------------------
#
#  Lane detection & Car distance System
# 
#  Python :      | NumPy : 
#  openCV :      | YOLO  : 
#
#--------------------------------------------------------------------------------

import cv2
import time         # for uart, debug (fps)
import serial       # for uart

import gData as g
from . import laneDet
from . import carDist


exit_flag = False



# --------------------------------------------------------------------------------
#
# --------------------------------------------------------------------------------

def Lds_setExit():
    global exit_flag
    exit_flag = True


# --------------------------------------------------------------------------------
#
# --------------------------------------------------------------------------------

def Lds_Stop(source):
    global exit_flag
    print('LDS END')
    if hasattr(source, "release"):
        source.release()
    cv2.destroyAllWindows()

    exit_flag = False


# --------------------------------------------------------------------------------
#  Set cam data (FHD -> HD)
# --------------------------------------------------------------------------------

def setCamHD( cap, width=1280, height=720 ):

    cap.set( cv2.CAP_PROP_FRAME_WIDTH, width )
    cap.set( cv2.CAP_PROP_FRAME_HEIGHT, height )


# --------------------------------------------------------------------------------
#  Convert video frame FHD -> HD
# --------------------------------------------------------------------------------

def convFrameHD( frame, width=1280, height=720 ):
   
    return cv2.resize( frame, (width, height) )


# --------------------------------------------------------------------------------
#  LDS Init ( Open lane source )
# --------------------------------------------------------------------------------

def Lds_Init( mode, path ):

    # jpg
    if mode == 0:  
        frame = cv2.imread( path )

        if frame is None:
            print( "Image file import error." )  
            return None
        
        return frame  
    
    # mp4
    if mode == 1:
        cap = cv2.VideoCapture( path )

        if not cap.isOpened():
            print( "Video file import error." )
            return None
        
        return cap
    
    # usb cam
    elif mode == 2:
        cap = cv2.VideoCapture( path )

        if not cap.isOpened():
            print( "USB camera import error." )
            return None
        
        setCamHD( cap )

        return cap  


# --------------------------------------------------------------------------------
#  LDS Run
# --------------------------------------------------------------------------------

def Lds_Run( mode, path, hef, label, queue):


    global exit_flag 


    # Init ( open video source )
    source = Lds_Init( mode, path )

    # Init hailo
    carDist.init_hailo_inference( hef, label )

    # UART init
    uart = serial.Serial('/dev/serial0', baudrate=115200)


    if source is None:
        exit()  

    if mode == 0:
        frame = convFrameHD( source )
        detFrame, hLine = laneDet.ldRun( frame )
        laneOffset = laneDet.ldOffset( detFrame ) 
        output_frame = cv2.addWeighted(detFrame, 1, laneOffset, 0.5, 0)

        cv2.imshow("Final Output", output_frame)

        cv2.waitKey(0)  

        Lds_Stop(source)
        return  
    
    else:

        prev_time = time.time()     # FPS test

        while source.isOpened():
            
            ## 07.29 종료 
            # if exit_flag:
            #     Lds_Stop(source)
            #     break
            if not queue.empty() :
                msg = queue.get()
                if msg == "EXIT":
                    print("[LDS] exit signal received")
                    break
                
            ret, frame = source.read()

            # Break loop(auto)
            if not ret:
                if mode == 1:
                    print("End of video.")
                elif mode == 2:
                    print("Unable to read frame.")

                break  

            # Video -> HD
            if mode == 1:
                frame = convFrameHD( frame ) 

            # 180 flip
            # rotated_frame = cv2.rotate(frame, cv2.ROTATE_180)
            # detFrame, hLine = laneDet.ldRun( rotated_frame )

            # Lane detect process
            detFrame, hLine = laneDet.ldRun( frame )
            laneOffset = laneDet.ldOffset( detFrame )

            # Get lane area
            laneArea = laneDet.getLaneArea( )

            # # Show Lane detect result
            # cv2.imshow("Lane Detection", detFrame)
            # cv2.imshow("Lane Detection Visualization", lane_det)

            # Run YOLO -> Get detect frame, detections
            detectedFrame, detections = carDist.runCarDet(detFrame)

            # Estimate distance
            carDist.getCarDist( detectedFrame, detections, laneArea )


            # Single mode (LDS->HUD)
            if g.car_dist == -1:
                #print( f"Lane Offset: {g.lane_offset}" )
                uart.write(f"$HUD,{g.lane_offset:.2f},-1.00\n".encode())
            else:
                #print(f"Lane Offset: {g.lane_offset}, dist : {g.car_dist:.2f} m")
                uart.write(f"$HUD,{g.lane_offset:.2f},{g.car_dist:.2f}\n".encode())
            

            # Final frame
            output_frame = cv2.addWeighted(detectedFrame, 1, laneOffset, 0.3, 0)

            # FPS test
            cur_time = time.time()
            fps = 1 / (cur_time - prev_time)
            prev_time = cur_time
            cv2.putText(output_frame, f"FPS: {fps:.2f}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            #

            # cv2.imshow("LaneDet Output", output_frame)
            cv2.imshow("Output Frame", cv2.resize(output_frame, (0, 0), fx=0.5, fy=0.5))

            # Break loop(manual)
            if cv2.waitKey(1) & 0xFF == ord('q'):       #!! chk fps
                Lds_Stop(source)
                break 
            
        ## 07.29 결과 전송
        cv2.destroyAllWindows()
        result_msg = "testData"
        queue.put(result_msg)

'''
Sample Command:-
python detect_aruco_images.py --image Images/1.png --type DICT_6X6_250
'''
import numpy as np
from utils import ARUCO_DICT, aruco_display, get_rec_points, get_centre
import argparse
import cv2
import sys


ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True, help="path to input image containing ArUCo tag")
ap.add_argument("-t", "--type", type=str, default="DICT_ARUCO_ORIGINAL", help="type of ArUCo tag to detect")
args = vars(ap.parse_args())


print("Loading image...")
image = cv2.imread(args["image"])
h, w, _ = image.shape
width = 1000
height = int(width*(h/w))
frame = cv2.resize(image, (width, height), interpolation=cv2.INTER_CUBIC)
img_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)


# verify that the supplied ArUCo tag exists and is supported by OpenCV
if ARUCO_DICT.get(args["type"], None) is None:
    print(f"ArUCo tag type '{args['type']}' is not supported")
    sys.exit(0)

# load the ArUCo dictionary, grab the ArUCo parameters, and detect the markers
print("Detecting '{}' tags....".format(args["type"]))
arucoDict = cv2.aruco.Dictionary_get(ARUCO_DICT[args["type"]])
arucoParams = cv2.aruco.DetectorParameters_create()

corners, ids, rejected = cv2.aruco.detectMarkers(img_gray, arucoDict, parameters=arucoParams)
detected_markers = cv2.aruco.drawDetectedMarkers(frame, corners, ids)

camera_matrix = np.load("calibration_matrix.npy")
dist_coeffs = np.load("distortion_coefficients.npy")


points = get_rec_points(corners)
if points is not None:
    for point in points:
        cv2.circle(frame, tuple(point), 4, (0, 0, 255), -1)

    org_h, org_w = 16.5, 18.5 #in cm
    points_3D = np.array([[-org_w/2, org_h/2, 0], [org_w/2, org_h/2, 0], [org_w/2, -org_h/2, 0], [-org_w/2, -org_h/2, 0]], dtype="double")
    
    points_2D = points.astype('float32')
    points_3D = points_3D.astype('float32')
 
    success, rvecs, tvecs = cv2.solvePnP(points_3D, points_2D, camera_matrix, dist_coeffs)
    
    len = 5 #in cm
    axis = np.float32([[-len/2, -len/2, 0], [-len/2, len/2, 0], [len/2, len/2, 0], [len/2, -len/2, 0],
                        [-len/2, -len/2, len], [-len/2, len/2, len], [len/2, len/2, len],[len/2, -len/2, len]])

    imgpts_2d, jac = cv2.projectPoints(axis, rvecs, tvecs, camera_matrix, dist_coeffs)
    imgpts_2d = np.int32(imgpts_2d).reshape(-1, 2)

    frame = cv2.drawContours(frame, [imgpts_2d[:4]], -1, (255, 0, 0), 2)
    for i, j in zip(range(4), range(4, 8)):
        frame = cv2.line(frame, tuple(imgpts_2d[i]), tuple(imgpts_2d[j]), (255, 0, 0), 2)
    frame = cv2.drawContours(frame, [imgpts_2d[4:]], -1, (255, 0, 0), 2)


    # points = np.float32(points)
    # width = 800
    # height = int(width*(org_h/org_w))
    # target_points = np.float32([[0, 0], [width, 0], [width, height], [0, height]])

    # M = cv2.getPerspectiveTransform(points, target_points)
    # warped = cv2.warpPerspective(frame, M, (width, height))

    # # cv2.imshow("Warped", warped)

cv2.imshow("Image", frame)

# # Uncomment to save
# cv2.imwrite("output_sample.png",detected_markers)

cv2.waitKey(0)

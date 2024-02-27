'''
python detect_aruco_video.py --type DICT_6X6_250 --camera True
python detect_aruco_video.py --type DICT_6X6_250 --camera False --video test_video.mp4
'''

from utils import ARUCO_DICT, aruco_display, get_rec_points, get_centre
import numpy as np
import argparse
import time
import cv2
import sys


ap = argparse.ArgumentParser()
ap.add_argument("-i", "--camera", required=True, help="Set to True if using webcam")
ap.add_argument("-v", "--video", help="Path to the video file")
ap.add_argument("-t", "--type", type=str, default="DICT_ARUCO_ORIGINAL", help="Type of ArUCo tag to detect")
args = vars(ap.parse_args())

if args["camera"].lower() == "true":
	video = cv2.VideoCapture(0)
	time.sleep(2.0)
	
else:
	if args["video"] is None:
		print("[Error] Video file location is not provided")
		sys.exit(1)

	video = cv2.VideoCapture(args["video"])

if ARUCO_DICT.get(args["type"], None) is None:
	print(f"ArUCo tag type '{args['type']}' is not supported")
	sys.exit(0)


arucoDict = cv2.aruco.Dictionary_get(ARUCO_DICT[args["type"]])
arucoParams = cv2.aruco.DetectorParameters_create()

camera_matrix = np.load("calibration_matrix.npy")
dist_coeffs = np.load("distortion_coefficients.npy")

while True:
	ret, img = video.read()	
	# img = cv2.flip(img, 1)
	if ret is False:
		break

	h, w, _ = img.shape

	width=800
	height = int(width*(h/w))
	frame = cv2.resize(img, (width, height), interpolation=cv2.INTER_CUBIC)
	img_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

	corners, ids, rejected = cv2.aruco.detectMarkers(img_gray, arucoDict, parameters=arucoParams)
	frame = cv2.aruco.drawDetectedMarkers(frame, corners, ids)

	points = get_rec_points(corners)
	if points is not None:
		for point in points:
			cv2.circle(frame, tuple(point), 4, (0, 0, 255), -1)

		org_h, org_w = 16.5, 18.5 #in cm
		points_3D = np.array([[-org_w/2, org_h/2, 0], [org_w/2, org_h/2, 0], [org_w/2, -org_h/2, 0], [-org_w/2, -org_h/2, 0]], dtype="double")
		
		points_2D = points.astype('float32')
		points_3D = points_3D.astype('float32')
	
		success, rvecs, tvecs = cv2.solvePnP(points_3D, points_2D, camera_matrix, dist_coeffs)
		
		len = 14 #in cm
		axis = np.float32([[-len/2, -len/2, 0], [-len/2, len/2, 0], [len/2, len/2, 0], [len/2, -len/2, 0],
							[-len/2, -len/2, len], [-len/2, len/2, len], [len/2, len/2, len],[len/2, -len/2, len]])

		imgpts_2d, jac = cv2.projectPoints(axis, rvecs, tvecs, camera_matrix, dist_coeffs)
		imgpts_2d = np.int32(imgpts_2d).reshape(-1, 2)

		frame = cv2.drawContours(frame, [imgpts_2d[:4]], -1, (255, 0, 0), 2)
		for i, j in zip(range(4), range(4, 8)):
			frame = cv2.line(frame, tuple(imgpts_2d[i]), tuple(imgpts_2d[j]), (0, 255, 10), 2)
		frame = cv2.drawContours(frame, [imgpts_2d[4:]], -1, (255, 0, 0), 2)

		points = np.float32(points)
		width = 800
		height = int(width*(org_h/org_w))
		target_points = np.float32([[0, 0], [width, 0], [width, height], [0, height]])

		M = cv2.getPerspectiveTransform(points, target_points)
		warped = cv2.warpPerspective(frame, M, (width, height))

		cv2.imshow("Warped", warped)
	cv2.imshow("Image", frame)

	key = cv2.waitKey(1) & 0xFF
	if key == ord("q"):
		break

cv2.destroyAllWindows()
video.release()
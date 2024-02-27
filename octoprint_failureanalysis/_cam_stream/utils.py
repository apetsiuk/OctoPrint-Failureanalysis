from flask import Response
import numpy as np
import os
from octoprint.settings import Settings
import cv2

def ar(input):
    """
    Returns the augmented input image
    """
    octoprint_settings = Settings()
    plugin_identifier = "Failureanalysis"
    aruco_type = octoprint_settings.get(["plugins", plugin_identifier, "aruco_type"])
    if aruco_type is None:
        aruco_type = "DICT_6X6_250"

    camera_matrix = np.load(os.path.dirname(__file__) + "\calibration_matrix.npy")
    dist_coeffs = np.load(os.path.dirname(__file__) + "\distortion_coefficients.npy")

    h, w, _ = input.shape
    width=800
    height = int(width*(h/w))
    frame = cv2.resize(input, (width, height), interpolation=cv2.INTER_CUBIC)
    img_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

    arucoDict = cv2.aruco.Dictionary_get(ARUCO_DICT[aruco_type])
    arucoParams = cv2.aruco.DetectorParameters_create()
    
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
		
        len = 10 #in cm
        axis = np.float32([[-len/2, -len/2, 0], [-len/2, len/2, 0], [len/2, len/2, 0], [len/2, -len/2, 0],
							[-len/2, -len/2, len], [-len/2, len/2, len], [len/2, len/2, len],[len/2, -len/2, len]])

        imgpts_2d, jac = cv2.projectPoints(axis, rvecs, tvecs, camera_matrix, dist_coeffs)
        imgpts_2d = np.int32(imgpts_2d).reshape(-1, 2)

        frame = cv2.drawContours(frame, [imgpts_2d[:4]], -1, (255, 0, 0), 2)
        for i, j in zip(range(4), range(4, 8)):
            frame = cv2.line(frame, tuple(imgpts_2d[i]), tuple(imgpts_2d[j]), (0, 255, 10), 2)
        frame = cv2.drawContours(frame, [imgpts_2d[4:]], -1, (255, 0, 0), 2)

    return frame

def is_valid_camera_ip(camera_ip):
    try:
        cap = cv2.VideoCapture(camera_ip)
        if cap.isOpened():
            cap.release()
            return True
        else:
            cap.release()
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    
def generate_feed(camera_ip):
    """
    Generates a video feed from the camera at the given index. stops video feed if its cut off/ cant read frame
    """
    if not is_valid_camera_ip(camera_ip):
        print("Invalid camera IP.")
        frame = cv2.imread(os.path.dirname(__file__) + "\error.jpg")
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    
    cap = cv2.VideoCapture(camera_ip)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = ar(frame)
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            break
        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    cap.release()


def generate_snapshot(camera_ip):
    """
    Generates snapshot from the camera at the given index. if the frame didnt return, return error
    """
    if not is_valid_camera_ip(camera_ip):
        print("Invalid camera IP.")
        frame = cv2.imread(os.path.dirname(__file__) + "\error.jpg")
        ret, buffer = cv2.imencode('.jpg', frame)
        yield Response(buffer.tobytes(), mimetype='image/jpeg')
    
    cap = cv2.VideoCapture(camera_ip)
    ret, frame = cap.read()
    if not ret:
        yield Response("error: could not capture frame")
    else:
        frame = ar(frame)
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            yield Response("error: could not encode frame")
        else:
            yield Response(buffer.tobytes(), mimetype='image/jpeg')
    cap.release()

def get_centre(corner):
    """
    Returns the centre of a rectangle
    """
    (topLeft, topRight, bottomRight, bottomLeft)  = corner.reshape((4, 2))
    return int((topLeft[0] + bottomRight[0]) / 2.0), int((topLeft[1] + bottomRight[1]) / 2.0)

def get_rec_points(corners):
    """
    Return the four corners of the rectangle that is formed by the centre of the detected four aruco markers
    """
    if len(corners) == 4:
        points = []
        for corner in corners:
            points.append(get_centre(corner))
        #sort based on y value
        points.sort(key=lambda x: x[1])
        #sort based on x value
        points[0:2] = sorted(points[0:2], key=lambda x: x[0])
        points[2:4] = sorted(points[2:4], key=lambda x: x[0], reverse=True)

        points = np.array(points)
        points = np.int32(points)
        return points
    else:
        return None


def aruco_display(corners, ids, rejected, image):
    if len(corners) > 0:
		# flatten the ArUco IDs list
        ids = ids.flatten()
        # loop over the detected ArUCo corners
        for (markerCorner, markerID) in zip(corners, ids):
            # extract the marker corners (which are always returned in
            # top-left, top-right, bottom-right, and bottom-left order)
            corners = markerCorner.reshape((4, 2))
            (topLeft, topRight, bottomRight, bottomLeft) = corners
			# convert each of the (x, y)-coordinate pairs to integers
            topRight = (int(topRight[0]), int(topRight[1]))
            bottomRight = (int(bottomRight[0]), int(bottomRight[1]))
            bottomLeft = (int(bottomLeft[0]), int(bottomLeft[1]))
            topLeft = (int(topLeft[0]), int(topLeft[1]))

            cv2.line(image, topLeft, topRight, (255, 0, 0), 2)
            cv2.line(image, topRight, bottomRight, (0, 255, 0), 2)
            cv2.line(image, bottomRight, bottomLeft, (0, 255, 0), 2)
            cv2.line(image, bottomLeft, topLeft, (0, 255, 0), 2)
			# compute and draw the center (x, y)-coordinates of the ArUco
			# marker
            cX = int((topLeft[0] + bottomRight[0]) / 2.0)
            cY = int((topLeft[1] + bottomRight[1]) / 2.0)
            cv2.circle(image, (cX, cY), 4, (0, 0, 255), -1)
			# draw the ArUco marker ID on the image
            cv2.putText(image, str(markerID),(topLeft[0], topLeft[1] - 10), cv2.FONT_HERSHEY_SIMPLEX,
				0.5, (0, 255, 0), 2)
            print("[Inference] ArUco marker ID: {}".format(markerID))
			# show the output image
    return image

ARUCO_DICT = {
	"DICT_4X4_50": cv2.aruco.DICT_4X4_50,
	"DICT_4X4_100": cv2.aruco.DICT_4X4_100,
	"DICT_4X4_250": cv2.aruco.DICT_4X4_250,
	"DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
	"DICT_5X5_50": cv2.aruco.DICT_5X5_50,
	"DICT_5X5_100": cv2.aruco.DICT_5X5_100,
	"DICT_5X5_250": cv2.aruco.DICT_5X5_250,
	"DICT_5X5_1000": cv2.aruco.DICT_5X5_1000,
	"DICT_6X6_50": cv2.aruco.DICT_6X6_50,
	"DICT_6X6_100": cv2.aruco.DICT_6X6_100,
	"DICT_6X6_250": cv2.aruco.DICT_6X6_250,
	"DICT_6X6_1000": cv2.aruco.DICT_6X6_1000,
	"DICT_7X7_50": cv2.aruco.DICT_7X7_50,
	"DICT_7X7_100": cv2.aruco.DICT_7X7_100,
	"DICT_7X7_250": cv2.aruco.DICT_7X7_250,
	"DICT_7X7_1000": cv2.aruco.DICT_7X7_1000,
	"DICT_ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
	"DICT_APRILTAG_16h5": cv2.aruco.DICT_APRILTAG_16h5,
	"DICT_APRILTAG_25h9": cv2.aruco.DICT_APRILTAG_25h9,
	"DICT_APRILTAG_36h10": cv2.aruco.DICT_APRILTAG_36h10,
	"DICT_APRILTAG_36h11": cv2.aruco.DICT_APRILTAG_36h11
}


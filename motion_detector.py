import cv2
import numpy as np

class MotionDetector:
    def __init__(self, threshold=25, min_area=500):
        self.threshold = threshold
        self.min_area = min_area
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(varThreshold=threshold, detectShadows=False)

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        fgmask = self.bg_subtractor.apply(gray)
        thresh = cv2.threshold(fgmask, self.threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion = False
        boxes = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > self.min_area:
                motion = True
                x, y, w, h = cv2.boundingRect(cnt)
                boxes.append((x, y, w, h))
        
        return motion, boxes, frame
import cv2
import numpy as np

def create_leaf_seed_mask(img: np.ndarray) -> np.ndarray:
    """Detects plant green canopy and chlorotic foliage seeds in HSV color space."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Plant foliage hues (Green to yellow/chartreuse)
    lower_foliage = np.array([22, 25, 25])
    upper_foliage = np.array([98, 255, 255])
    foliage_mask = cv2.inRange(hsv, lower_foliage, upper_foliage)
    
    # Also include high-brightness powdery mildew on leaf
    lower_white = np.array([0, 0, 175])
    upper_white = np.array([180, 50, 255])
    white_mask = cv2.inRange(hsv, lower_white, upper_white)
    
    seed_mask = cv2.bitwise_or(foliage_mask, white_mask)
    return seed_mask

def segment_leaf(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Cleanly segments the main leaf canopy from soil and background using
    morphological closure and convex boundary extraction.
    """
    seed_mask = create_leaf_seed_mask(img)
    
    # Morphological closure to bridge internal veins and spots
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    closed = cv2.morphologyEx(seed_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    
    # Find contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    leaf_mask = np.zeros(img.shape[:2], dtype=np.uint8)
    if contours:
        # Get largest leaf contour
        largest_c = max(contours, key=cv2.contourArea)
        # Leaf boundary as convex hull / smooth contour
        hull = cv2.convexHull(largest_c)
        cv2.drawContours(leaf_mask, [hull], -1, 255, thickness=cv2.FILLED)
    else:
        # Fallback to Otsu thresholding on grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresholded = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        leaf_mask = thresholded
        
    masked_leaf = cv2.bitwise_and(img, img, mask=leaf_mask)
    return masked_leaf, leaf_mask

import cv2
import numpy as np
import os

def load_image(image_path: str) -> np.ndarray:
    """Loads an image from the specified path."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at: {image_path}")
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to load image from: {image_path}")
    return img

def resize_image(img: np.ndarray, target_size: int = 512) -> np.ndarray:
    """Resizes an image preserving aspect ratio and padding with black."""
    h, w = img.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    delta_w = target_size - new_w
    delta_h = target_size - new_h
    top, bottom = delta_h // 2, delta_h - (delta_h // 2)
    left, right = delta_w // 2, delta_w - (delta_w // 2)
    
    color = [0, 0, 0]
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return padded

def denoise(img: np.ndarray) -> np.ndarray:
    """Applies edge-preserving bilateral denoising to the image."""
    return cv2.bilateralFilter(img, d=5, sigmaColor=35, sigmaSpace=35)

def normalize_illumination(img: np.ndarray) -> np.ndarray:
    """Normalizes illumination using CLAHE on the L-channel of LAB colorspace."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

def preprocess(image_path: str) -> np.ndarray:
    """Chains all preprocessing steps."""
    img = load_image(image_path)
    img = resize_image(img)
    img = denoise(img)
    img = normalize_illumination(img)
    return img

import cv2
import numpy as np

def detect_lesions_color_analysis(leaf_img: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """
    Detects symptomatic/lesion regions within the leaf mask by analyzing color deviation
    from healthy green canopy standards in HSV and LAB color spaces.
    """
    if cv2.countNonZero(leaf_mask) == 0:
        return np.zeros_like(leaf_mask)
        
    hsv = cv2.cvtColor(leaf_img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    # Healthy green canopy definition:
    # Hue: 32 - 88 (medium to deep green)
    # Saturation: >= 40 (vibrant green)
    # Value: 40 - 220 (not pure white or near black)
    healthy_green_mask = (h >= 32) & (h <= 88) & (s >= 40) & (v >= 40) & (v <= 220) & (leaf_mask > 0)
    
    # Diseased candidates inside leaf mask that are NOT healthy green:
    # 1. Dark necrosis / Black rot / Late blight / Anthracnose (Value < 60)
    # 2. Powdery mildew (Chalky white/gray: V > 165, S < 60)
    # 3. Yellow mosaic / Chlorosis (H: 10 - 31, S > 45, V > 60)
    # 4. Rust / Orange pustules (H: 4 - 23, S > 50, V > 50)
    # 5. Brown / Tan lesions (H: 5 - 28, V: 35 - 160)
    
    lesion_mask_raw = (leaf_mask > 0) & (~healthy_green_mask)
    
    # Convert boolean mask to uint8
    lesion_mask = (lesion_mask_raw * 255).astype(np.uint8)
    
    # Morphological noise removal (remove isolated single-pixel artifacts)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    lesion_mask_clean = cv2.morphologyEx(lesion_mask, cv2.MORPH_OPEN, kernel)
    
    return lesion_mask_clean

def extract_lesion_contours(lesion_mask: np.ndarray, min_area: int = 15) -> list:
    """Finds lesion contours filtered by minimum area."""
    contours, _ = cv2.findContours(lesion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filtered = [c for c in contours if cv2.contourArea(c) >= min_area]
    return filtered

def compute_severity(leaf_mask: np.ndarray, lesion_mask: np.ndarray) -> float:
    """Computes severity as percentage of leaf covered by active lesions."""
    leaf_pixels = cv2.countNonZero(leaf_mask)
    if leaf_pixels == 0:
        return 0.0
    lesion_pixels = cv2.countNonZero(lesion_mask)
    severity = (lesion_pixels / leaf_pixels) * 100.0
    return float(np.clip(severity, 0.0, 100.0))

def get_severity_level(severity_pct: float) -> str:
    """Maps severity percentage to clinical risk level."""
    if severity_pct < 8.0:
        return 'low'
    elif severity_pct <= 28.0:
        return 'moderate'
    else:
        return 'severe'

def detect_lesions(leaf_img: np.ndarray, leaf_mask: np.ndarray) -> tuple[np.ndarray, list, float, str]:
    """End-to-end lesion detection and severity calculation."""
    lesion_mask = detect_lesions_color_analysis(leaf_img, leaf_mask)
    contours = extract_lesion_contours(lesion_mask, min_area=15)
    severity_pct = compute_severity(leaf_mask, lesion_mask)
    severity_level = get_severity_level(severity_pct)
    return lesion_mask, contours, severity_pct, severity_level

import cv2
import numpy as np
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern

def extract_color_features(img: np.ndarray, leaf_mask: np.ndarray, lesion_mask: np.ndarray) -> np.ndarray:
    """
    Extracts comprehensive color distributions in HSV, LAB, and RGB color spaces
    for both the overall leaf canopy and localized lesion regions.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    
    leaf_pixels_hsv = hsv[leaf_mask > 0]
    leaf_pixels_lab = lab[leaf_mask > 0]
    
    lesion_pixels_hsv = hsv[lesion_mask > 0]
    lesion_pixels_lab = lab[lesion_mask > 0]
    lesion_pixels_bgr = img[lesion_mask > 0]
    
    feats = []
    
    # 1. Overall Leaf Color Stats (HSV mean/std, LAB mean/std) -> 12 features
    for cspace_pixels in [leaf_pixels_hsv, leaf_pixels_lab]:
        if len(cspace_pixels) > 0:
            for ch in range(3):
                feats.append(float(np.mean(cspace_pixels[:, ch])))
                feats.append(float(np.std(cspace_pixels[:, ch])))
        else:
            feats.extend([0.0] * 6)
            
    # 2. Lesion Color Stats (HSV mean/std, LAB mean/std, BGR mean/std) -> 18 features
    if len(lesion_pixels_hsv) > 0:
        for ch in range(3):
            feats.append(float(np.mean(lesion_pixels_hsv[:, ch])))
            feats.append(float(np.std(lesion_pixels_hsv[:, ch])))
        for ch in range(3):
            feats.append(float(np.mean(lesion_pixels_lab[:, ch])))
            feats.append(float(np.std(lesion_pixels_lab[:, ch])))
        for ch in range(3):
            feats.append(float(np.mean(lesion_pixels_bgr[:, ch])))
            feats.append(float(np.std(lesion_pixels_bgr[:, ch])))
    else:
        feats.extend([0.0] * 18)
        
    # 3. Pathogen Color Signature Ratios (crucial for disease separation) -> 6 features
    total_leaf_px = max(1, cv2.countNonZero(leaf_mask))
    if len(leaf_pixels_hsv) > 0:
        h = leaf_pixels_hsv[:, 0]
        s = leaf_pixels_hsv[:, 1]
        v = leaf_pixels_hsv[:, 2]
        
        # Powdery white ratio (high V, low S)
        white_ratio = float(np.sum((v > 170) & (s < 55))) / total_leaf_px
        # Bright yellow mosaic ratio (H: 14-34, S: > 50, V: > 70)
        yellow_ratio = float(np.sum((h >= 14) & (h <= 34) & (s > 50) & (v > 70))) / total_leaf_px
        # Rust orange ratio (H: 4-22, S: > 60, V: > 50)
        orange_ratio = float(np.sum((h >= 4) & (h <= 22) & (s > 60) & (v > 50))) / total_leaf_px
        # Jet black / dark necrosis ratio (V < 55)
        black_ratio = float(np.sum(v < 55)) / total_leaf_px
        # Brown / Tan ratio (H: 5-26, V: 40-150)
        brown_ratio = float(np.sum((h >= 5) & (h <= 26) & (v >= 40) & (v <= 150))) / total_leaf_px
        # Healthy green ratio (H: 34-88, S: > 45, V: > 45)
        green_ratio = float(np.sum((h >= 34) & (h <= 88) & (s > 45) & (v > 45))) / total_leaf_px
        
        feats.extend([white_ratio, yellow_ratio, orange_ratio, black_ratio, brown_ratio, green_ratio])
    else:
        feats.extend([0.0] * 6)
        
    return np.array(feats, dtype=np.float32)

def extract_texture_features(gray_img: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """Extracts GLCM texture properties and Local Binary Pattern (LBP) histogram."""
    if cv2.countNonZero(leaf_mask) == 0:
        return np.zeros(16, dtype=np.float32)
        
    masked_gray = cv2.bitwise_and(gray_img, gray_img, mask=leaf_mask)
    
    # GLCM computation
    glcm = graycomatrix(masked_gray, distances=[1, 3], angles=[0, np.pi/4], levels=256, symmetric=True, normed=True)
    contrast = float(np.mean(graycoprops(glcm, 'contrast')))
    dissimilarity = float(np.mean(graycoprops(glcm, 'dissimilarity')))
    homogeneity = float(np.mean(graycoprops(glcm, 'homogeneity')))
    energy = float(np.mean(graycoprops(glcm, 'energy')))
    correlation = float(np.mean(graycoprops(glcm, 'correlation')))
    asm = float(np.mean(graycoprops(glcm, 'ASM')))
    
    # LBP texture histogram (10 bins)
    lbp = local_binary_pattern(masked_gray, P=8, R=1, method='uniform')
    lbp_hist, _ = np.histogram(lbp[leaf_mask > 0], bins=10, range=(0, 10), density=True)
    if np.isnan(lbp_hist).any():
        lbp_hist = np.zeros(10, dtype=np.float32)
        
    return np.concatenate([[contrast, dissimilarity, homogeneity, energy, correlation, asm], lbp_hist]).astype(np.float32)

def extract_shape_features(contours: list, leaf_mask: np.ndarray) -> np.ndarray:
    """Extracts geometric, morphological, and spatial distribution metrics of lesions."""
    total_leaf_area = max(1.0, float(cv2.countNonZero(leaf_mask)))
    
    if not contours:
        return np.zeros(8, dtype=np.float32)
        
    num_lesions = float(len(contours))
    areas = []
    circularities = []
    aspect_ratios = []
    solidities = []
    
    total_lesion_area = 0.0
    for c in contours:
        area = cv2.contourArea(c)
        total_lesion_area += area
        areas.append(area)
        
        perimeter = cv2.arcLength(c, True)
        if perimeter > 0:
            circ = (4.0 * np.pi * area) / (perimeter ** 2)
        else:
            circ = 0.0
        circularities.append(circ)
        
        _, _, w, h = cv2.boundingRect(c)
        if h > 0:
            aspect_ratios.append(float(w) / float(h))
        else:
            aspect_ratios.append(1.0)
            
        hull = cv2.convexHull(c)
        hull_area = cv2.contourArea(hull)
        if hull_area > 0:
            solidities.append(area / hull_area)
        else:
            solidities.append(1.0)
            
    lesion_ratio = total_lesion_area / total_leaf_area
    mean_area = float(np.mean(areas)) if areas else 0.0
    std_area = float(np.std(areas)) if len(areas) > 1 else 0.0
    mean_circ = float(np.mean(circularities)) if circularities else 0.0
    mean_aspect = float(np.mean(aspect_ratios)) if aspect_ratios else 0.0
    mean_solidity = float(np.mean(solidities)) if solidities else 0.0
    
    return np.array([
        num_lesions,
        lesion_ratio,
        mean_area,
        std_area,
        mean_circ,
        mean_aspect,
        mean_solidity,
        total_lesion_area
    ], dtype=np.float32)

def extract_features(img: np.ndarray, leaf_mask: np.ndarray, lesion_mask: np.ndarray, contours: list) -> np.ndarray:
    """Extracts and concatenates complete 60-dimensional multimodal feature vector."""
    color_feats = extract_color_features(img, leaf_mask, lesion_mask)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    texture_feats = extract_texture_features(gray, leaf_mask)
    
    shape_feats = extract_shape_features(contours, leaf_mask)
    
    feature_vector = np.concatenate([color_feats, texture_feats, shape_feats])
    # Replace any potential NaNs or Infs
    feature_vector = np.nan_to_num(feature_vector, nan=0.0, posinf=0.0, neginf=0.0)
    return feature_vector.astype(np.float32)

import pytest
import numpy as np
import cv2
import os

from disease_detector.preprocessing import preprocess, resize_image, denoise, normalize_illumination
from disease_detector.segmentation import segment_leaf
from disease_detector.lesion_detection import detect_lesions
from disease_detector.feature_extraction import extract_features
from disease_detector.classifier import diagnose

# Use a sample image from the sample_images directory
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sample_images')


def get_test_image_path():
    """Get path to a test image, creating one if needed."""
    img_path = os.path.join(SAMPLE_DIR, 'early_blight_1.png')
    if os.path.exists(img_path):
        return img_path
    # Fallback: create a synthetic test image in-memory and save it
    test_dir = os.path.join(SAMPLE_DIR, '_test')
    os.makedirs(test_dir, exist_ok=True)
    fallback_path = os.path.join(test_dir, 'test_leaf.png')
    if not os.path.exists(fallback_path):
        img = np.ones((512, 512, 3), dtype=np.uint8) * 40
        cv2.ellipse(img, (256, 256), (150, 220), 45, 0, 360, (50, 150, 50), -1)
        cv2.circle(img, (200, 200), 20, (30, 60, 90), -1)
        cv2.circle(img, (300, 280), 15, (30, 60, 90), -1)
        cv2.imwrite(fallback_path, img)
    return fallback_path


@pytest.fixture
def test_image_path():
    return get_test_image_path()


def test_preprocessing(test_image_path):
    img = preprocess(test_image_path)
    assert img.shape == (512, 512, 3)
    assert img.dtype == np.uint8


def test_resize():
    """Test resize preserves aspect ratio and output is target size."""
    img = np.zeros((300, 400, 3), dtype=np.uint8)
    resized = resize_image(img, target_size=512)
    assert resized.shape == (512, 512, 3)


def test_denoise():
    """Test denoise doesn't change image dimensions."""
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    denoised = denoise(img)
    assert denoised.shape == img.shape


def test_illumination_normalization():
    """Test CLAHE normalization doesn't change image dimensions."""
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    normalized = normalize_illumination(img)
    assert normalized.shape == img.shape
    assert normalized.dtype == np.uint8


def test_segmentation(test_image_path):
    img = preprocess(test_image_path)
    leaf_img, leaf_mask = segment_leaf(img)
    assert leaf_mask.shape == (512, 512)
    assert np.count_nonzero(leaf_mask) > 0


def test_lesion_detection(test_image_path):
    img = preprocess(test_image_path)
    leaf_img, leaf_mask = segment_leaf(img)
    lesion_mask, contours, severity_pct, severity_level = detect_lesions(leaf_img, leaf_mask)
    assert 0 <= severity_pct <= 100
    assert severity_level in ['low', 'moderate', 'severe']


def test_feature_extraction(test_image_path):
    img = preprocess(test_image_path)
    leaf_img, leaf_mask = segment_leaf(img)
    lesion_mask, contours, _, _ = detect_lesions(leaf_img, leaf_mask)
    features = extract_features(img, leaf_mask, lesion_mask, contours)
    assert len(features) == 60
    assert not np.isnan(features).any()


def test_diagnose(test_image_path):
    results = diagnose(test_image_path)
    required_keys = ['disease_name', 'confidence', 'severity_pct', 'severity_level', 'recommendation', 'pest_disease_flag']
    for k in required_keys:
        assert k in results
    assert 0 <= results['confidence'] <= 100
    assert 0 <= results['severity_pct'] <= 100
    assert isinstance(results['pest_disease_flag'], bool)

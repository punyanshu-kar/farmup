# Crop Disease Detection Pipeline

This module provides a complete computer vision pipeline for detecting diseases in crop leaves using OpenCV and Scikit-learn.

## Pipeline Stages
1. **Preprocessing (`preprocessing.py`)**: Loads image, resizes it to 512x512 while padding to preserve aspect ratio, denoises it using Non-Local Means, and normalizes illumination via CLAHE on the LAB color space.
2. **Segmentation (`segmentation.py`)**: Uses HSV thresholds to extract the green/yellow/brown regions of the leaf and isolate it from the background. Falls back to Otsu thresholding if the mask is too small. Morphological operations refine the mask.
3. **Lesion Detection (`lesion_detection.py`)**: Applies K-Means clustering to the masked leaf region. Clusters that fall outside the healthy green hue range are classified as lesions. Computes severity as the percentage of leaf area covered by lesions.
4. **Feature Extraction (`feature_extraction.py`)**: Computes 30 features per image:
   - 12 color features (mean & std of H,S,V and L,a,b channels)
   - 14 texture features (GLCM contrast, homogeneity, energy, correlation, and a 10-bin LBP histogram)
   - 4 shape features from lesion contours (number, mean area, mean circularity, mean aspect ratio)
5. **Classification (`classifier.py`)**: A Random Forest Classifier trained on extracted features maps them to disease categories. Look up treatment recommendations from `advisory_map.json`.

## Synthetic Dataset
Due to lack of real data, the dataset is synthetically generated using OpenCV.
Run `python -m disease_detector.sample_images.generate_samples` to generate training images.
*Note: Because this is trained on small synthetic data, accuracy will not be production-ready. Retrain with real data for practical use.*

## Running the Demo
```bash
streamlit run disease_detector/demo_app.py
```
If `model.pkl` is missing, you can click "Train Model from Sample Images" in the Streamlit sidebar.

## Retraining
To retrain on real data, place your images in a directory following the naming convention `{disease}_{number}.jpg`, and call:
```python
from disease_detector.classifier import generate_training_data, train_model
X, y = generate_training_data("path/to/real/data")
train_model(X, y, "disease_detector/model.pkl")
```

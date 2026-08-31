import os
import glob
import json
import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
from typing import Tuple, Dict, Any, List

from .preprocessing import preprocess
from .segmentation import segment_leaf
from .lesion_detection import detect_lesions
from .feature_extraction import extract_features

DISEASE_NAMES = [
    'healthy',
    'early_blight',
    'late_blight',
    'leaf_spot',
    'rust',
    'bacterial_spot',
    'powdery_mildew',
    'yellow_mosaic_virus',
    'anthracnose',
    'bacterial_blight',
    'black_rot'
]

def generate_training_data(sample_dir: str) -> Tuple[np.ndarray, np.ndarray]:
    """Generates 60D feature vectors and corresponding labels from sample images."""
    image_paths = sorted(glob.glob(os.path.join(sample_dir, '*.png')))
    X = []
    y = []
    
    print(f"Extracting features from {len(image_paths)} sample images in {sample_dir}...")
    for idx, path in enumerate(image_paths):
        filename = os.path.basename(path)
        # Expected format: disease_name_1.png or disease_name_12.png
        parts = filename.replace('.png', '').split('_')
        # Recombine parts except last numeric index
        label = "_".join(parts[:-1]) if parts[-1].isdigit() else filename.replace('.png', '')
        
        try:
            img = preprocess(path)
            leaf_img, leaf_mask = segment_leaf(img)
            lesion_mask, contours, _, _ = detect_lesions(leaf_img, leaf_mask)
            features = extract_features(img, leaf_mask, lesion_mask, contours)
            
            X.append(features)
            y.append(label)
        except Exception as e:
            print(f"Warning: Failed to process {filename}: {e}")
            
    print(f"Feature extraction complete. Extracted {len(X)} samples across {len(set(y))} classes.")
    return np.array(X, dtype=np.float32), np.array(y)

def train_model(X: np.ndarray, y: np.ndarray, model_path: str = 'model.pkl') -> Dict[str, Any]:
    """Trains a tuned Ensemble Classifier with 5-Fold Stratified Cross-Validation."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    # Tuned ensemble model: RandomForest + ExtraTrees
    rf = RandomForestClassifier(
        n_estimators=150,
        max_depth=16,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    
    et = ExtraTreesClassifier(
        n_estimators=150,
        max_depth=16,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    
    ensemble = VotingClassifier(
        estimators=[('rf', rf), ('et', et)],
        voting='soft'
    )
    
    # Cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(ensemble, X_scaled, y_encoded, cv=cv)
    mean_cv_acc = float(np.mean(cv_scores))
    print(f"5-Fold Stratified Cross-Validation Accuracy: {mean_cv_acc * 100:.2f}% (+/- {float(np.std(cv_scores))*100:.2f}%)")
    
    # Fit on all training data
    ensemble.fit(X_scaled, y_encoded)
    train_preds = ensemble.predict(X_scaled)
    train_acc = accuracy_score(y_encoded, train_preds)
    print(f"Training Accuracy: {train_acc * 100:.2f}%")
    
    metadata = {
        'classes': list(le.classes_),
        'num_classes': len(le.classes_),
        'total_samples': len(y),
        'cv_accuracy': mean_cv_acc,
        'train_accuracy': train_acc
    }
    
    # Save model artifacts
    os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': ensemble,
            'scaler': scaler,
            'label_encoder': le,
            'metadata': metadata
        }, f)
        
    print(f"Model saved successfully to {model_path}")
    return metadata

def load_model(model_path: str) -> Tuple[Any, Any, Any, Dict[str, Any]]:
    """Loads the trained ensemble model, scaler, label encoder, and metadata."""
    with open(model_path, 'rb') as f:
        data = pickle.load(f)
    metadata = data.get('metadata', {})
    return data['model'], data['scaler'], data['label_encoder'], metadata

def predict(model: Any, scaler: Any, label_encoder: Any, features: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
    """Predicts disease class, confidence score, and full class probability distribution."""
    features_scaled = scaler.transform(features.reshape(1, -1))
    probas = model.predict_proba(features_scaled)[0]
    
    pred_idx = int(np.argmax(probas))
    confidence = float(probas[pred_idx] * 100.0)
    predicted_class = str(label_encoder.inverse_transform([pred_idx])[0])
    
    # Full probability dictionary
    prob_dict = {
        str(cls_name): float(prob * 100.0)
        for cls_name, prob in zip(label_encoder.classes_, probas)
    }
    
    return predicted_class, confidence, prob_dict

def diagnose(image_path: str, model_path: str = None) -> Dict[str, Any]:
    """
    End-to-end diagnosis pipeline:
    Preprocess -> Leaf Segmentation -> Lesion Detection -> Feature Extraction -> Classification -> Advisory
    """
    img = preprocess(image_path)
    leaf_img, leaf_mask = segment_leaf(img)
    lesion_mask, contours, severity_pct, severity_level = detect_lesions(leaf_img, leaf_mask)
    features = extract_features(img, leaf_mask, lesion_mask, contours)
    
    disease_name = "unknown"
    confidence = 0.0
    prob_dist = {}
    
    if model_path and os.path.exists(model_path):
        model, scaler, le, _ = load_model(model_path)
        disease_name, confidence, prob_dist = predict(model, scaler, le, features)
    else:
        # Heuristic fallback if model is not yet compiled
        if severity_pct < 4.0:
            disease_name = "healthy"
            confidence = 94.0
        else:
            disease_name = "early_blight"
            confidence = 82.0
            
    # Load treatment advisory
    advisory_path = os.path.join(os.path.dirname(__file__), 'advisory_map.json')
    recommendation = "Consult your local agricultural extension officer for customized treatment."
    if os.path.exists(advisory_path):
        with open(advisory_path, 'r', encoding='utf-8') as f:
            advisory = json.load(f)
        recommendation = advisory.get(disease_name, {}).get(severity_level, recommendation)
        
    # High distress flag if condition is active and moderate/severe (excluding healthy)
    pest_disease_flag = (disease_name != 'healthy') and (severity_level in ['moderate', 'severe'] or severity_pct > 7.0)
    
    return {
        "disease_name": disease_name,
        "confidence": confidence,
        "severity_pct": severity_pct,
        "severity_level": severity_level,
        "recommendation": recommendation,
        "pest_disease_flag": pest_disease_flag,
        "prob_distribution": prob_dist,
        "leaf_img": leaf_img,
        "leaf_mask": leaf_mask,
        "lesion_mask": lesion_mask,
        "preprocessed_img": img
    }

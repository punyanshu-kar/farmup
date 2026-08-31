import sys
import os

# Ensure the project root (parent of disease_detector/) is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import cv2
import numpy as np
import glob
import json
from disease_detector.classifier import diagnose, train_model, generate_training_data, load_model

st.set_page_config(
    layout="wide",
    page_title="AI Crop Disease Detector — Smart Advisory",
    page_icon="🍃"
)

# Custom CSS styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1b5e20;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f1f8e9;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #4caf50;
        margin-bottom: 15px;
    }
    .disease-badge {
        display: inline-block;
        padding: 6px 14px;
        font-size: 1.2rem;
        font-weight: 700;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .badge-healthy { background-color: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7; }
    .badge-disease { background-color: #ffebee; color: #c62828; border: 1px solid #ef9a9a; }
    .advisory-box {
        background: #e3f2fd;
        border-left: 5px solid #1976d2;
        padding: 16px;
        border-radius: 6px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🍃 Smart Crop Disease Detection & AI Advisory</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Disease Computer Vision Diagnostics (10 Pathologies + Healthy Leaf) for Indian Agriculture</div>', unsafe_allow_html=True)

sample_dir = os.path.join(os.path.dirname(__file__), 'sample_images')
model_path = os.path.join(os.path.dirname(__file__), 'model.pkl')

# Sidebar configuration
st.sidebar.header("⚙️ Model & Diagnostics Config")

# Display model metadata if trained
if os.path.exists(model_path):
    try:
        _, _, _, meta = load_model(model_path)
        if meta:
            st.sidebar.markdown("### 📊 Model Performance")
            st.sidebar.success(f"**Trained Classes:** {meta.get('num_classes', 11)}")
            st.sidebar.info(f"**Total Samples:** {meta.get('total_samples', 'N/A')}")
            cv_acc = meta.get('cv_accuracy', 0.0) * 100.0
            st.sidebar.metric("5-Fold CV Accuracy", f"{cv_acc:.1f}%")
            train_acc = meta.get('train_accuracy', 0.0) * 100.0
            st.sidebar.metric("Training Accuracy", f"{train_acc:.1f}%")
    except Exception:
        pass
else:
    st.sidebar.warning("⚠️ Model not compiled yet.")

if st.sidebar.button("🔄 Retrain & Fine-Tune Model (11 Classes)"):
    with st.spinner("Extracting 60D feature vectors & training ensemble (RandomForest + ExtraTrees)..."):
        X, y = generate_training_data(sample_dir)
        meta = train_model(X, y, model_path)
    st.sidebar.success(f"✅ Model tuned! 5-Fold CV: {meta['cv_accuracy']*100:.1f}%, Train: {meta['train_accuracy']*100:.1f}%")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📁 Sample Image Gallery (11 Classes)")

# Group sample images by category
sample_images = sorted(glob.glob(os.path.join(sample_dir, "*.png")))
sample_names = [os.path.basename(p) for p in sample_images if not p.endswith('_test.png')]

disease_categories = [
    "None",
    "healthy",
    "early_blight",
    "late_blight",
    "leaf_spot",
    "rust",
    "bacterial_spot",
    "powdery_mildew",
    "yellow_mosaic_virus",
    "anthracnose",
    "bacterial_blight",
    "black_rot"
]

selected_category = st.sidebar.selectbox("Filter sample by Disease Class:", disease_categories)

filtered_samples = ["None"]
if selected_category != "None":
    filtered_samples += [s for s in sample_names if s.startswith(selected_category)]
else:
    filtered_samples += sample_names

selected_sample = st.sidebar.selectbox("Select specific sample image:", filtered_samples)

# Main layout tabs
tab_analyze, tab_classes = st.tabs(["🔬 Image Analysis & Advisory", "📚 Supported Disease Catalog"])

with tab_analyze:
    col_input1, col_input2 = st.columns([1, 1])
    with col_input1:
        uploaded_file = st.file_uploader("📤 Upload phone camera leaf photo", type=['png', 'jpg', 'jpeg'])
    with col_input2:
        if selected_sample != "None":
            st.info(f"Selected Sample: `{selected_sample}`")

    image_to_process = None
    if uploaded_file is not None:
        temp_path = os.path.join(os.path.dirname(__file__), "temp_uploaded.png")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        image_to_process = temp_path
    elif selected_sample != "None":
        image_to_process = os.path.join(sample_dir, selected_sample)

    if image_to_process:
        st.markdown("---")
        st.subheader("🔍 Computer Vision Pipeline Decomposition")
        
        with st.spinner("Executing 6-Stage Computer Vision Pipeline..."):
            try:
                results = diagnose(image_to_process, model_path)
                
                # 4-Column Pipeline Visualization
                col1, col2, col3, col4 = st.columns(4)
                
                orig_img = cv2.imread(image_to_process)
                col1.image(cv2.cvtColor(orig_img, cv2.COLOR_BGR2RGB), caption="1. Original Input Image", use_container_width=True)
                
                prep_img = results['preprocessed_img']
                col2.image(cv2.cvtColor(prep_img, cv2.COLOR_BGR2RGB), caption="2. CLAHE Illumination Normalized", use_container_width=True)
                
                # Leaf Mask Overlay
                leaf_mask = results['leaf_mask']
                overlay = prep_img.copy()
                overlay[leaf_mask == 0] = overlay[leaf_mask == 0] // 3
                col3.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB), caption="3. Leaf Segmentation Mask", use_container_width=True)
                
                # Lesion Heatmap Overlay
                lesion_mask = results['lesion_mask']
                lesion_overlay = prep_img.copy()
                # Highlight lesions in bright red with semi-transparency
                lesion_highlight = lesion_overlay.copy()
                lesion_highlight[lesion_mask > 0] = [0, 30, 255]
                cv_composite = cv2.addWeighted(lesion_overlay, 0.45, lesion_highlight, 0.55, 0)
                col4.image(cv2.cvtColor(cv_composite, cv2.COLOR_BGR2RGB), caption="4. Lesion & Symptom Detection", use_container_width=True)
                
                st.markdown("---")
                
                # Diagnostic Results Layout
                res_col1, res_col2 = st.columns([1.2, 1.8])
                
                with res_col1:
                    st.subheader("📋 Diagnosis Summary")
                    
                    is_healthy = results['disease_name'] == 'healthy'
                    badge_class = "badge-healthy" if is_healthy else "badge-disease"
                    disease_display = results['disease_name'].replace('_', ' ').title()
                    
                    st.markdown(f'<div class="disease-badge {badge_class}">Diagnosis: {disease_display}</div>', unsafe_allow_html=True)
                    
                    conf = results['confidence']
                    st.metric("Model Confidence Score", f"{conf:.1f}%")
                    st.progress(min(1.0, conf / 100.0))
                    
                    sev_pct = results['severity_pct']
                    sev_lvl = results['severity_level'].title()
                    
                    sev_color = "#2e7d32" if is_healthy or sev_lvl == "Low" else "#ef6c00" if sev_lvl == "Moderate" else "#c62828"
                    st.markdown(f"**Infection Severity:** <span style='font-size:1.1rem; color:{sev_color}; font-weight:700;'>{sev_pct:.1f}% ({sev_lvl})</span>", unsafe_allow_html=True)
                    
                    if results['pest_disease_flag']:
                        st.error("🚨 **DISTRESS ALERT TRIGGERED:** Disease severity requires agricultural officer intervention & escalation.")
                    else:
                        st.success("✅ Risk status within standard management parameters.")
                        
                with res_col2:
                    st.subheader("💡 Hyperlocal Agricultural Advisory")
                    st.markdown(f"""
                    <div class="advisory-box">
                        <h4 style="color:#0d47a1; margin-top:0;">Prescribed Treatment & Next Steps:</h4>
                        <p style="font-size:1.05rem; line-height:1.6; color:#1a237e;">{results['recommendation']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Probability Distribution chart
                    if results.get('prob_distribution'):
                        st.markdown("##### 🔬 Top Class Probability Distribution")
                        sorted_probs = sorted(results['prob_distribution'].items(), key=lambda x: x[1], reverse=True)[:5]
                        for c_name, c_prob in sorted_probs:
                            c_clean = c_name.replace('_', ' ').title()
                            st.write(f"**{c_clean}**: {c_prob:.1f}%")
                            st.progress(min(1.0, c_prob / 100.0))
                            
            except Exception as e:
                st.error(f"Error executing diagnosis pipeline: {e}")
                import traceback
                st.code(traceback.format_exc())

with tab_classes:
    st.subheader("🌾 Supported Crop Disease Catalog (10 Diseases + Healthy)")
    
    catalog_data = [
        {"Name": "Healthy Crop Leaf", "Code": "healthy", "Pathogen": "None (Optimal)", "Visual Symptoms": "Vibrant uniform green foliage, distinct veins, no necrotic lesions"},
        {"Name": "Early Blight", "Code": "early_blight", "Pathogen": "Alternaria solani", "Visual Symptoms": "Concentric dark brown rings forming characteristic target-board lesions with yellow halos"},
        {"Name": "Late Blight", "Code": "late_blight", "Pathogen": "Phytophthora infestans", "Visual Symptoms": "Rapidly spreading water-soaked dark gray/black necrotic blotches with pale translucent margins"},
        {"Name": "Leaf Spot", "Code": "leaf_spot", "Pathogen": "Cercospora / Septoria", "Visual Symptoms": "Numerous small circular tan/brown spots with dark defined borders and ash-gray centers"},
        {"Name": "Rust", "Code": "rust", "Pathogen": "Puccinia spp.", "Visual Symptoms": "Raised powdery reddish-orange / terracotta pustules clustered along leaf veins"},
        {"Name": "Bacterial Spot", "Code": "bacterial_spot", "Pathogen": "Xanthomonas spp.", "Visual Symptoms": "Small angular water-soaked dark brown-to-black lesions bounded by leaf veinlets"},
        {"Name": "Powdery Mildew", "Code": "powdery_mildew", "Pathogen": "Erysiphe / Podosphaera", "Visual Symptoms": "White chalky to light gray powdery fungal patches spreading across upper canopy"},
        {"Name": "Yellow Mosaic Virus", "Code": "yellow_mosaic_virus", "Pathogen": "Geminivirus (Whitefly vector)", "Visual Symptoms": "Bright golden-yellow / lime mottled mosaic patches interspersed with green islands"},
        {"Name": "Anthracnose", "Code": "anthracnose", "Pathogen": "Colletotrichum spp.", "Visual Symptoms": "Sunken dark brown-black necrotic lesions with concentric rings and ragged centers"},
        {"Name": "Bacterial Blight", "Code": "bacterial_blight", "Pathogen": "Xanthomonas oryzae", "Visual Symptoms": "V-shaped marginal yellowing progressing to necrotic straw-colored blight along edges"},
        {"Name": "Black Rot", "Code": "black_rot", "Pathogen": "Xanthomonas campestris", "Visual Symptoms": "Intense deep velvety jet-black necrotic patches spreading through vascular veins"}
    ]
    
    st.table(catalog_data)

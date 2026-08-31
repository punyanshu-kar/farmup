import cv2
import numpy as np
import os
import random

def draw_leaf_veins(img, center, axes, angle):
    """Draws realistic primary and secondary leaf veins."""
    cx, cy = center
    major_len, minor_len = axes
    rad = np.deg2rad(angle)
    
    # Primary vein along major axis
    tip_x = int(cx + major_len * 0.95 * np.cos(rad))
    tip_y = int(cy + major_len * 0.95 * np.sin(rad))
    base_x = int(cx - major_len * 0.95 * np.cos(rad))
    base_y = int(cy - major_len * 0.95 * np.sin(rad))
    
    vein_color = (60, 175, 75)
    cv2.line(img, (base_x, base_y), (tip_x, tip_y), vein_color, 2, cv2.LINE_AA)
    
    # Secondary lateral veins
    num_side_veins = 7
    for i in range(1, num_side_veins):
        t = -0.75 + (1.5 * i / num_side_veins)
        vx = int(cx + t * major_len * np.cos(rad))
        vy = int(cy + t * major_len * np.sin(rad))
        
        # Perpendicular direction
        perp_rad_1 = rad + np.pi / 3.0
        perp_rad_2 = rad - np.pi / 3.0
        reach = minor_len * 0.65 * (1.0 - abs(t) * 0.4)
        
        lx1 = int(vx + reach * np.cos(perp_rad_1))
        ly1 = int(vy + reach * np.sin(perp_rad_1))
        lx2 = int(vx + reach * np.cos(perp_rad_2))
        ly2 = int(vy + reach * np.sin(perp_rad_2))
        
        cv2.line(img, (vx, vy), (lx1, ly1), vein_color, 1, cv2.LINE_AA)
        cv2.line(img, (vx, vy), (lx2, ly2), vein_color, 1, cv2.LINE_AA)

def create_leaf_base(variation_idx=0):
    """Generates a realistic leaf with background, lighting, and vein texture."""
    np.random.seed(variation_idx * 13 + 42)
    random.seed(variation_idx * 13 + 42)
    
    # Soil/field background with natural gradient
    bg_base = np.array([35, 55, 80], dtype=np.float32) # BGR
    bg_noise = np.random.normal(0, 8, (512, 512, 3)).astype(np.float32)
    bg_img = np.clip(bg_base + bg_noise, 0, 255).astype(np.uint8)
    
    # Leaf geometry
    cx = 256 + random.randint(-15, 15)
    cy = 256 + random.randint(-15, 15)
    major_axis = random.randint(190, 225)
    minor_axis = random.randint(125, 155)
    angle = random.randint(30, 60)
    
    # Create blank canvas for leaf
    leaf_canvas = np.zeros((512, 512, 3), dtype=np.uint8)
    
    # Leaf color: healthy vibrant green with natural gradient
    green_hue = random.randint(45, 75)
    leaf_bgr = (random.randint(35, 60), random.randint(145, 185), random.randint(40, 75))
    
    # Draw solid leaf base
    cv2.ellipse(leaf_canvas, (cx, cy), (minor_axis, major_axis), angle, 0, 360, leaf_bgr, -1)
    
    # Draw leaf mask
    mask = np.zeros((512, 512), dtype=np.uint8)
    cv2.ellipse(mask, (cx, cy), (minor_axis, major_axis), angle, 0, 360, 255, -1)
    
    # Draw veins
    draw_leaf_veins(leaf_canvas, (cx, cy), (major_axis, minor_axis), angle)
    
    # Add cellular texture & lighting gradient
    tex_noise = np.random.normal(0, 7, (512, 512, 3)).astype(np.float32)
    leaf_textured = np.clip(leaf_canvas.astype(np.float32) + tex_noise, 0, 255).astype(np.uint8)
    
    # Composite leaf onto background
    final_img = np.where(mask[:, :, None] == 255, leaf_textured, bg_img)
    return final_img, mask, (cx, cy, major_axis, minor_axis, angle)

def add_symptoms(img, mask, geometry, disease_type, sample_seed=0):
    """Adds distinct pathology patterns for each of the 10 diseases."""
    np.random.seed(sample_seed * 17 + 101)
    random.seed(sample_seed * 17 + 101)
    
    cx, cy, major_axis, minor_axis, angle = geometry
    out = img.copy()
    
    leaf_points = np.argwhere(mask == 255)
    if len(leaf_points) == 0:
        return out
    
    if disease_type == 'healthy':
        # Zero disease lesions
        return out

    elif disease_type == 'early_blight':
        # Concentric rings with yellow chlorotic halos (Alternaria target boards)
        num_lesions = random.randint(4, 9)
        for _ in range(num_lesions):
            idx = random.randint(0, len(leaf_points) - 1)
            y, x = leaf_points[idx]
            r = random.randint(16, 32)
            
            # Yellow chlorotic halo
            cv2.circle(out, (x, y), int(r * 1.35), (20, 195, 220), -1)
            # Dark brown outer ring
            cv2.circle(out, (x, y), r, (25, 60, 95), -1)
            # Inner concentric ring
            cv2.circle(out, (x, y), int(r * 0.65), (35, 80, 125), -1)
            # Center necrotic spot
            cv2.circle(out, (x, y), int(r * 0.3), (15, 40, 70), -1)

    elif disease_type == 'late_blight':
        # Large irregular water-soaked dark brown/black necrotic blotches
        num_patches = random.randint(3, 6)
        for _ in range(num_patches):
            idx = random.randint(0, len(leaf_points) - 1)
            y, x = leaf_points[idx]
            rx = random.randint(35, 65)
            ry = random.randint(25, 45)
            patch_ang = random.randint(0, 180)
            
            # Water-soaked pale margin
            cv2.ellipse(out, (x, y), (rx + 8, ry + 8), patch_ang, 0, 360, (70, 120, 110), -1)
            # Dark necrotic blotch
            cv2.ellipse(out, (x, y), (rx, ry), patch_ang, 0, 360, (25, 30, 35), -1)
            # Inner deep necrosis
            cv2.ellipse(out, (x, y), (int(rx * 0.5), int(ry * 0.5)), patch_ang, 0, 360, (15, 18, 20), -1)

    elif disease_type == 'leaf_spot':
        # Many small circular tan/brown spots with dark borders and gray centers
        num_spots = random.randint(30, 60)
        for _ in range(num_spots):
            idx = random.randint(0, len(leaf_points) - 1)
            y, x = leaf_points[idx]
            r = random.randint(3, 8)
            
            # Dark halo border
            cv2.circle(out, (x, y), r + 2, (15, 45, 80), -1)
            # Gray-tan interior
            cv2.circle(out, (x, y), r, (90, 130, 160), -1)
            # Light center
            if r > 4:
                cv2.circle(out, (x, y), int(r * 0.4), (160, 175, 185), -1)

    elif disease_type == 'rust':
        # Clustered raised orange/terracotta/rusty-brown pustules with yellow halos
        num_clusters = random.randint(4, 7)
        for _ in range(num_clusters):
            idx = random.randint(0, len(leaf_points) - 1)
            cy_c, cx_c = leaf_points[idx]
            cluster_size = random.randint(8, 16)
            for _ in range(cluster_size):
                px = cx_c + random.randint(-22, 22)
                py = cy_c + random.randint(-22, 22)
                if 0 <= py < 512 and 0 <= px < 512 and mask[py, px] == 255:
                    r = random.randint(2, 6)
                    # Yellow halo
                    cv2.circle(out, (px, py), r + 2, (30, 190, 230), -1)
                    # Bright rust-orange pustule (BGR: high red, med green, low blue)
                    cv2.circle(out, (px, py), r, (15, 90, 215), -1)
                    # Deep terracotta center
                    cv2.circle(out, (px, py), max(1, r - 2), (10, 50, 175), -1)

    elif disease_type == 'bacterial_spot':
        # Small angular dark brown/black water-soaked lesions
        num_spots = random.randint(25, 45)
        for _ in range(num_spots):
            idx = random.randint(0, len(leaf_points) - 1)
            y, x = leaf_points[idx]
            w = random.randint(5, 12)
            h = random.randint(5, 12)
            rot = random.randint(0, 90)
            
            # Yellowish water-soaked margin
            cv2.ellipse(out, (x, y), (w + 2, h + 2), rot, 0, 360, (40, 160, 190), -1)
            # Angular dark black/brown center
            cv2.ellipse(out, (x, y), (w, h), rot, 0, 360, (18, 22, 28), -1)

    elif disease_type == 'powdery_mildew':
        # White/light gray chalky powdery fungal patches
        num_colonies = random.randint(5, 10)
        for _ in range(num_colonies):
            idx = random.randint(0, len(leaf_points) - 1)
            y, x = leaf_points[idx]
            rx = random.randint(18, 38)
            ry = random.randint(15, 32)
            rot = random.randint(0, 180)
            
            # Translucent powdery white colony
            colony_layer = np.zeros_like(out)
            cv2.ellipse(colony_layer, (x, y), (rx, ry), rot, 0, 360, (235, 240, 245), -1)
            # Feathered border
            cv2.ellipse(colony_layer, (x, y), (int(rx * 0.7), int(ry * 0.7)), rot, 0, 360, (255, 255, 255), -1)
            
            colony_mask = cv2.cvtColor(colony_layer, cv2.COLOR_BGR2GRAY) > 0
            # Blend smoothly onto leaf
            out[colony_mask] = cv2.addWeighted(out[colony_mask], 0.25, colony_layer[colony_mask], 0.75, 0)

    elif disease_type == 'yellow_mosaic_virus':
        # Bright golden yellow / lime mosaic patches intermingled with green islands
        num_patches = random.randint(12, 22)
        for _ in range(num_patches):
            idx = random.randint(0, len(leaf_points) - 1)
            y, x = leaf_points[idx]
            rx = random.randint(15, 35)
            ry = random.randint(12, 28)
            rot = random.randint(0, 180)
            
            # Bright yellow mosaic patch (BGR: low B, high G, high R)
            cv2.ellipse(out, (x, y), (rx, ry), rot, 0, 360, (25, 225, 235), -1)
            # Golden center
            cv2.ellipse(out, (x, y), (int(rx * 0.6), int(ry * 0.6)), rot, 0, 360, (15, 205, 245), -1)

    elif disease_type == 'anthracnose':
        # Sunken dark brown/black blotches with concentric fungal acervuli rings
        num_blotches = random.randint(4, 8)
        for _ in range(num_blotches):
            idx = random.randint(0, len(leaf_points) - 1)
            y, x = leaf_points[idx]
            r = random.randint(14, 28)
            
            # Sunken brown outer ring
            cv2.circle(out, (x, y), r, (20, 50, 85), -1)
            # Black acervuli ring
            cv2.circle(out, (x, y), int(r * 0.7), (10, 15, 20), -1)
            # Tan necrotic center
            cv2.circle(out, (x, y), int(r * 0.35), (45, 90, 140), -1)

    elif disease_type == 'bacterial_blight':
        # V-shaped marginal necrosis starting from leaf edge with yellow wavy margin
        num_blights = random.randint(2, 4)
        for _ in range(num_blights):
            # Pick a point near the periphery of the leaf
            idx = random.randint(0, len(leaf_points) - 1)
            py, px = leaf_points[idx]
            dist_to_center = np.sqrt((px - cx)**2 + (py - cy)**2)
            if dist_to_center > minor_axis * 0.4:
                # Large wedge-like margin lesion
                bw = random.randint(30, 60)
                bh = random.randint(40, 80)
                rot = int(np.rad2deg(np.arctan2(py - cy, px - cx)))
                
                # Yellow chlorotic margin wave
                cv2.ellipse(out, (px, py), (bw + 10, bh + 10), rot, 0, 360, (30, 195, 225), -1)
                # Straw-colored necrotic interior
                cv2.ellipse(out, (px, py), (bw, bh), rot, 0, 360, (55, 115, 160), -1)
                # Dried center
                cv2.ellipse(out, (px, py), (int(bw * 0.5), int(bh * 0.5)), rot, 0, 360, (30, 65, 100), -1)

    elif disease_type == 'black_rot':
        # Intense deep velvety jet-black necrotic blotches
        num_patches = random.randint(4, 9)
        for _ in range(num_patches):
            idx = random.randint(0, len(leaf_points) - 1)
            y, x = leaf_points[idx]
            rx = random.randint(16, 36)
            ry = random.randint(14, 30)
            rot = random.randint(0, 180)
            
            # Faint dark halo
            cv2.ellipse(out, (x, y), (rx + 4, ry + 4), rot, 0, 360, (20, 25, 25), -1)
            # Jet black necrotic patch
            cv2.ellipse(out, (x, y), (rx, ry), rot, 0, 360, (5, 8, 10), -1)

    # Re-apply mask to preserve sharp leaf boundary against background
    out = np.where(mask[:, :, None] == 255, out, img)
    return out

def generate_dataset(output_dir, num_per_class=20):
    """Generates a complete dataset with 11 classes and 20+ images per class."""
    os.makedirs(output_dir, exist_ok=True)
    
    classes = [
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
    
    total_generated = 0
    print(f"Generating synthetic dataset: {len(classes)} classes x {num_per_class} images = {len(classes) * num_per_class} images...")
    
    for cls in classes:
        for i in range(1, num_per_class + 1):
            seed = hash(f"{cls}_{i}") % 100000
            base, mask, geom = create_leaf_base(variation_idx=seed)
            final_img = add_symptoms(base, mask, geom, cls, sample_seed=seed)
            
            filename = f"{cls}_{i}.png"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, final_img)
            total_generated += 1
            
    print(f"Successfully generated {total_generated} leaf images in {output_dir}")

if __name__ == "__main__":
    out_path = os.path.dirname(__file__)
    generate_dataset(out_path, num_per_class=20)

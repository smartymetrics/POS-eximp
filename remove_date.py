from PIL import Image
import numpy as np
import os

img_path = r"C:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\IMG-20260325-WA0037.jpg"
out_path = r"C:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\stamp_clean.jpg"

try:
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found")
        exit(1)
        
    img = Image.open(img_path).convert('RGB')
    arr = np.array(img)
    
    h, w = arr.shape[:2]
    
    # Pen ink is blue in RGB: a simple heuristic to detect blue pixels
    R = arr[:,:,0].astype(int)
    G = arr[:,:,1].astype(int)
    B = arr[:,:,2].astype(int)
    
    # Blue is higher than Red and Green
    is_blue = (B > R + 20) & (B > G + 10) & (B > 80)
    
    # Restrict to region where date is (top right-ish)
    # y: 25% to 55%, x: 35% to 90%
    y1, y2 = int(h * 0.25), int(h * 0.55)
    x1, x2 = int(w * 0.35), int(w * 0.90)
    
    mask = np.zeros((h, w), dtype=bool)
    mask[y1:y2, x1:x2] = True
    
    # Combine masks to only target blue things in the top right
    target_pixels = is_blue & mask
    
    # Replace target blue pixels with white
    arr[target_pixels] = [255, 255, 255]
    
    # Try an alternative: maybe just a white rectangle over the exact text bounds 
    # if the blue detection is not perfect, but detection usually maintains the lines.
    # Let's save it
    out_img = Image.fromarray(arr.astype('uint8'))
    out_img.save(out_path)
    print(f"Success: saved to {out_path}")
except Exception as e:
    print("Error:", e)

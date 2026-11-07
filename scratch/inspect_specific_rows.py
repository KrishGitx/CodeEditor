from PIL import Image
import numpy as np

img = Image.open(r"C:/Users/amazi/.gemini/antigravity/brain/c89cc1ce-b008-4beb-8be2-8d660fe01472/.user_uploaded/media_1794051510403_3e08f5bc.png")
arr = np.array(img.convert('RGB'))

for y, label in [(268, "page.goto("), (365, "print(page.title())"), (380, "print(page.url)"), (418, "textbox = page.get_by_role(")]:
    row = arr[y, :, :]
    print(f"\n--- {label} (y={y}) ---")
    for x in range(40, 52):
        print(f"x={x}: {list(row[x])}")


import numpy as np
import matplotlib.pyplot as plt
import json

mask = np.load("lf/sample_mask.npy")

with open("lf/sample_mask_meta.json") as f:
    meta = json.load(f)

minx = meta["utm_min_x"]
miny = meta["utm_min_y"]
res  = meta["resolution"]

H, W = mask.shape

extent = (minx, minx + W*res, miny, miny + H*res)

plt.imshow(mask, cmap="gray", extent=extent, origin="lower")
plt.title("Road Mask in UTM Coordinates")
plt.xlabel("UTM X")
plt.ylabel("UTM Y")
plt.show()

import cv2
import numpy as np
import matplotlib.pyplot as plt

mask = np.load("lf/sample_mask.npy").astype(np.uint8)

# 이진화(혹시 필요할 수 있어서)
binary = (mask > 0).astype(np.uint8) * 255

# skeleton thinning
skeleton = cv2.ximgproc.thinning(binary)

plt.imshow(skeleton, cmap="gray")
plt.title("Skeleton")
plt.show()

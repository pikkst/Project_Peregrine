import airsim
import os
import cv2
import numpy as np
import time

OUTPUT_DIR = "sim/data_collection/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

client = airsim.MultirotorClient()
client.confirmConnection()

request = [
    airsim.ImageRequest("0", airsim.ImageType.Scene, False, False),
    airsim.ImageRequest("0", airsim.ImageType.DepthPerspective, True, False),
    airsim.ImageRequest("0", airsim.ImageType.Segmentation, False, False),
]

for i in range(200):
    responses = client.simGetImages(request)
    rgb = np.frombuffer(responses[0].image_data_uint8, dtype=np.uint8)
    rgb = rgb.reshape(responses[0].height, responses[0].width, 3)

    depth = airsim.list_to_2d_float_array(responses[1].image_data_float,
                                          responses[1].width,
                                          responses[1].height)

    seg = np.frombuffer(responses[2].image_data_uint8, dtype=np.uint8)
    seg = seg.reshape(responses[2].height, responses[2].width, 3)

    cv2.imwrite(os.path.join(OUTPUT_DIR, f"rgb_{i:04d}.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    np.save(os.path.join(OUTPUT_DIR, f"depth_{i:04d}.npy"), depth)
    cv2.imwrite(os.path.join(OUTPUT_DIR, f"seg_{i:04d}.png"), cv2.cvtColor(seg, cv2.COLOR_RGB2BGR))

    time.sleep(0.1)

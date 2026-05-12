import airsim
import time

client = airsim.MultirotorClient()
client.confirmConnection()
client.enableApiControl(True)
client.armDisarm(True)

client.takeoffAsync().join()
client.moveToZAsync(-5, 1).join()

client.moveToPositionAsync(10, 0, -5, 3).join()
client.moveToPositionAsync(10, 10, -5, 3).join()
client.moveToPositionAsync(0, 10, -5, 3).join()
client.moveToPositionAsync(0, 0, -5, 3).join()

client.landAsync().join()
client.armDisarm(False)
client.enableApiControl(False)

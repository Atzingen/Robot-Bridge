import gc
import micropython
import hub_runtime

micropython.alloc_emergency_exception_buf(256)

# hub_runtime.start()


# import ble_temperature
# ble_temperature.demo()

import hub

bt = hub.BT_VCP()



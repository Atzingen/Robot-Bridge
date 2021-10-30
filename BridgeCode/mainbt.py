# Hub to hub remote control program. Run this on the remote control

# Full tutorial here:
# https://antonsmindstorms.com/2021/06/19/how-to-remote-control-lego-spike-prime-and-robot-inventor-with-python/

# TO STOP THIS SCRIPT ALWAYS USE THE BUTTON ON THE HUB. 
# AVOID THE STOP BUTTON IN THE MINDSTORSM APP!

# Building instructions here: 
# https://antonsmindstorms.com/product/remote-control-transmitter-with-mindstorms-51515/

# Use with the the car script here:
# https://gist.github.com/antonvh/88548d95e771043662f038de451e28f2
#... or with the tank script here:
# https://gist.github.com/antonvh/aca9e9a32aaebe337af3fb1a6f2712aa

# Authors: Anton's Mindstorms & Ste7an.

# Most of it is library bluetooth code.
# Scroll to line 360 for the core program.

# Finds a robot with bluetooth peripheral service, advertising under the default name 'robot'
# After connicting this script sends a bytestring with joystick positions 30 times per second.
# Format "bbbbBBiiB", l_stick_hor, l_stick_ver, r_stick_hor, r_stick_ver, l_trigger, r_trigger, setting1, setting2, buttons_char


# ===== This should probably go into an import one day ===== #
import bluetooth
import random
import struct
import time
import micropython
import ubinascii
# from hub import display, Image
from micropython import const

# Used irqs: _IRQ_SCAN_DONE, _IRQ_SCAN_RESULT, _IRQ_PERIPHERAL_CONNECT, _IRQ_PERIPHERAL_DISCONNECT,
# _IRQ_GATTC_SERVICE_RESULT, _IRQ_GATTC_SERVICE_DONE, _IRQ_GATTC_CHARACTERISTIC_RESULT,
# _IRQ_GATTC_WRITE_DONE, _IRQ_GATTC_NOTIFY, _IRQ_GATTC_READ_RESULT

_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_WRITE_DONE = const(17)

if 'FLAG_INDICATE' in dir(bluetooth):
    # We're on MINDSTORMS Robot Inventor
    # New version of bluetooth
    _IRQ_SCAN_RESULT = 5
    _IRQ_SCAN_DONE = 6
    _IRQ_PERIPHERAL_CONNECT = 7
    _IRQ_PERIPHERAL_DISCONNECT = 8
    _IRQ_GATTC_SERVICE_RESULT = 9
    _IRQ_GATTC_CHARACTERISTIC_RESULT = 11
    _IRQ_GATTC_READ_RESULT = 15
    _IRQ_GATTC_NOTIFY = 18
    _IRQ_GATTC_CHARACTERISTIC_DONE = 12
else:
    # We're probably on SPIKE Prime
    _IRQ_SCAN_RESULT = 1 << 4
    _IRQ_SCAN_DONE = 1 << 5
    _IRQ_PERIPHERAL_CONNECT = 1 << 6
    _IRQ_PERIPHERAL_DISCONNECT = 1 << 7
    _IRQ_GATTC_SERVICE_RESULT = 1 << 8
    _IRQ_GATTC_CHARACTERISTIC_RESULT = 1 << 9
    _IRQ_GATTC_READ_RESULT = 1 << 11
    _IRQ_GATTC_NOTIFY = 1 << 13
    _IRQ_GATTC_CHARACTERISTIC_DONE = 1 << 12


_NOTIFY_ENABLE = const(1)
_INDICATE_ENABLE = const(2)


_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_RX = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

# Advertising payloads are repeated packets of the following form:
#1 byte data length (N + 1)
#1 byte type (see constants below)
#N bytes type-specific data

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID32_COMPLETE = const(0x5)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_UUID16_MORE = const(0x2)
_ADV_TYPE_UUID32_MORE = const(0x4)
_ADV_TYPE_UUID128_MORE = const(0x6)
_ADV_TYPE_APPEARANCE = const(0x19)


# Generate a payload to be passed to gap_advertise(adv_data=...).
def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    payload = bytearray()

    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack("BB", len(value) + 1, adv_type) + value

    _append(
        _ADV_TYPE_FLAGS,
        struct.pack("B", (0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)),
    )

    if name:
        _append(_ADV_TYPE_NAME, name)

    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(_ADV_TYPE_UUID16_COMPLETE, b)
            elif len(b) == 4:
                _append(_ADV_TYPE_UUID32_COMPLETE, b)
            elif len(b) == 16:
                _append(_ADV_TYPE_UUID128_COMPLETE, b)

    # See org.bluetooth.characteristic.gap.appearance.xml
    if appearance:
        _append(_ADV_TYPE_APPEARANCE, struct.pack("<h", appearance))

    return payload


def decode_field(payload, adv_type):
    i = 0
    result = []
    while i + 1 < len(payload):
        if payload[i + 1] == adv_type:
            result.append(payload[i + 2 : i + payload[i] + 1])
        i += 1 + payload[i]
    return result


def decode_name(payload):
    n = decode_field(payload, _ADV_TYPE_NAME)
    return str(n[0], "utf-8") if n else ""


def decode_services(payload):
    services = []
    for u in decode_field(payload, _ADV_TYPE_UUID16_COMPLETE):
        services.append(bluetooth.UUID(struct.unpack("<h", u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID32_COMPLETE):
        services.append(bluetooth.UUID(struct.unpack("<d", u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID128_COMPLETE):
        services.append(bluetooth.UUID(u))
    return services

def show_logo(data):
    pass
    # if data[:5] == b'Image':
    #     print('show logo', eval(data))
    # else:
    #     print(data)


class BLESimpleCentral:
    def __init__(self, ble=None):
        if ble == None:
            ble = bluetooth.BLE()
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._reset()

    def _reset(self):
        # Cached name and address from a successful scan.
        self._name = None
        self._addr_type = None
        self._addr = None

        # Callbacks for completion of various operations.
        # These reset back to None after being invoked.
        self._scan_callback = None
        self._conn_callback = None
        self._read_callback = None

        # Persistent callback for when new data is notified from the device.
        self._notify_callback = show_logo

        # Connected device.
        self._conn_handle = None
        self._start_handle = None
        self._end_handle = None
        self._tx_handle = None
        self._rx_handle = None

        self._n=0


    def _on_scan(self, addr_type, addr, name):
        if addr_type is not None:
            print("Found peripheral:", addr_type, addr, name)
            time.sleep_ms(500)
            self.connect()
        else:
            self.timed_out = True
            print("No uart peripheral '{}' found.".format(self._search_name))

    def scan_connect(self, name="robot"):
        self.timed_out = False
        self.scan(search_name=name, callback=self._on_scan)
        while not self.is_connected() and not self.timed_out:
            # print("Waiting for connection...")
            time.sleep_ms(10)
        return not self.timed_out

    def _irq(self, event, data):
        if event not in (_IRQ_SCAN_DONE, _IRQ_SCAN_RESULT, _IRQ_PERIPHERAL_CONNECT, _IRQ_PERIPHERAL_DISCONNECT, 
                        _IRQ_GATTC_SERVICE_RESULT, _IRQ_GATTC_SERVICE_DONE, _IRQ_GATTC_CHARACTERISTIC_RESULT,
                        _IRQ_GATTC_WRITE_DONE, _IRQ_GATTC_NOTIFY, _IRQ_GATTC_READ_RESULT, _IRQ_GATTC_CHARACTERISTIC_DONE):
            print(event, hex(event))

        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            name=decode_name(adv_data) or "?"
            # print('type:{} addr:{} name:{} adv_type: {} rssi:{} data:{}'.format(addr_type, ubinascii.hexlify(addr), name, adv_type,rssi,ubinascii.hexlify(adv_data)))
            if name == self._search_name:
                # Found a potential device, remember it
                self._addr_type = addr_type
                self._addr = bytes(addr) # Note: addr buffer is owned by caller so need to copy it.
                self._name = name
                # ... and stop scanning. This triggers the IRQ_SCAN_DONE and the on_scan callback.
                self._ble.gap_scan(None)

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            # Called once service discovery is complete.
            # Note: Status will be zero on success, implementation-specific value otherwise.
            # conn_handle, status = data
            pass

        elif event == _IRQ_SCAN_DONE:
            if self._scan_callback:
                if self._addr:
                    # Found a device during the scan (and the scan was explicitly stopped).
                    self._scan_callback(self._addr_type, self._addr, self._name)
                    self._scan_callback = None
                else:
                    # Scan timed out.
                    self._scan_callback(None, None, None)

        elif event == _IRQ_PERIPHERAL_CONNECT:
            # Connect successful.
            conn_handle, addr_type, addr = data
            if addr_type == self._addr_type and addr == self._addr:
                self._conn_handle = conn_handle
                self._ble.gattc_discover_services(self._conn_handle)

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # Disconnect (either initiated by us or the remote end).
            conn_handle, _, _ = data
            if conn_handle == self._conn_handle:
                # If it was initiated by us, it'll already be reset.
                self._reset()
                print("Disconnect from peripheral")
                self.timed_out = True

        elif event == _IRQ_GATTC_SERVICE_RESULT:
            # Connected device returned a service.
            conn_handle, start_handle, end_handle, uuid = data
            self._n+=1
            if conn_handle == self._conn_handle and uuid == _UART_UUID:
                self._start_handle, self._end_handle = start_handle, end_handle
                # print("UART_UID handles",data)
                time.sleep_ms(500)
                self._ble.gattc_discover_characteristics(self._conn_handle, start_handle, end_handle)


        elif event == _IRQ_GATTC_SERVICE_DONE:
            time.sleep_ms(300)
            # Service query complete.
            if self._start_handle and self._end_handle:
                self._ble.gattc_discover_characteristics(
                    self._conn_handle, self._start_handle, self._end_handle
                )
            else:
                print("Failed to find uart service.")
                self.timed_out = True

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            # Connected device returned a characteristic.
            conn_handle, def_handle, value_handle, properties, uuid = data
            #print('gattc_char',data)
            if conn_handle == self._conn_handle:
                if uuid == _UART_RX:
                    self._rx_handle = value_handle
                elif uuid == _UART_TX:
                    self._tx_handle = value_handle

        elif event == _IRQ_GATTC_WRITE_DONE:
            conn_handle, value_handle, status = data
            print("TX complete")

        elif event == _IRQ_GATTC_NOTIFY:
            # print("_IRQ_GATTC_NOTIFY")
            conn_handle, value_handle, notify_data = data
            notify_data=bytes(notify_data)

            if conn_handle == self._conn_handle and value_handle == self._tx_handle:
                if self._notify_callback:
                    self._notify_callback(notify_data)

        elif event == _IRQ_GATTC_READ_RESULT:
            #print("_IRQ_GATTC_READ_RESULT")
            # A read completed successfully.
            conn_handle, value_handle, char_data = data
            if conn_handle == self._conn_handle and value_handle in (self._rx_handle,self._buta_handle,self._butb_handle):
                # print("handle,READ data",value_handle,bytes(char_data))
                self._read_callback(value_handle,bytes(char_data))


    # Returns true if we've successfully connected and discovered uart characteristics.
    def is_connected(self):
        return (
            self._conn_handle is not None
            and self._tx_handle is not None
            and self._rx_handle is not None
        )

    # Find a device advertising the uart service.
    def scan(self, search_name=None, callback=None):
        self._addr_type = None
        self._addr = None
        self._search_name=search_name
        self._scan_callback = callback
        self._ble.gap_scan(20000, 30000, 30000)

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, addr_type=None, addr=None, callback=None):
        self._addr_type = addr_type or self._addr_type
        self._addr = addr or self._addr
        self._conn_callback = callback
        if self._addr_type is None or self._addr is None:
            return False
        self._ble.gap_connect(self._addr_type, self._addr)
        return True

    # Disconnect from current device.
    def disconnect(self):
        if not self._conn_handle:
            return
        self._ble.gap_disconnect(self._conn_handle)
        self._reset()

    # Send data over the UART
    def write(self, v, response=False):
        if not self.is_connected():
            return
        self._ble.gattc_write(self._conn_handle, self._rx_handle, v, 1 if response else 0)

    # def enable_notify(self):
    #    if not self.is_connected():
    #        return
    #    print("Enabled notify")
    #    #self._ble.gattc_write(self._conn_handle, self._acc_handle, struct.pack('<h', _NOTIFY_ENABLE), 0)
    #    for i in range(38,49):
    #        self._ble.gattc_write(self._conn_handle, i, struct.pack('<h', _NOTIFY_ENABLE), 0)
    #        time.sleep_ms(50)
    #    print("notified enabled")

    def read(self,handle,callback):
        if not self.is_connected():
            return
        self._read_callback = callback
        try:
            self._ble.gattc_read(self._conn_handle, handle)
        except:
            pass
            #print("gattc_read failed")

    # Set handler for when data is received over the UART.
    def on_notify(self, callback):
        # self.enable_notify()
        self._notify_callback = callback
        # print("callback",callback)

# ===== End of library import bit. Now the real code. ===== #
from machine import Pin, ADC
from time import sleep

# Initialize
print("starting BLE")
remote_control = BLESimpleCentral()

print("Scanning & connecting")
found = remote_control.scan_connect()

pot = ADC(Pin(34))
pot.atten(ADC.ATTN_11DB)       #Full range: 3.3v
btn = Pin(12, Pin.IN, Pin.PULL_UP)

if not found:
    print ("Scanning timed out")
    del(remote_control)
    raise SystemExit

print("Connected")

# Use this if you want te receive data back from the robot
# Note that printing doesn't work here. It messes up comms.
# def on_rx(v):
#     pass
#     # print("RX", v)

# central.on_notify(on_rx)

# This can probably be less. TODO.
time.sleep_ms(1000)



while remote_control.is_connected():
    beep = 1
    buttons_char = 0
    buttons=[0]*8
    if btn.value():
        beep = 0
        buttons[0] = True

    # Create a byte with ones for each pressed button.
    for i in range(len(buttons)):
        if buttons[i]:
            buttons_char += 1 << i

    pot_pos = int(pot.read()*200/4095) - 100

    # Pack and transmit all remote control values
    controller_state = struct.pack("bbbbBBiiB",
        pot_pos,   #clamp_int(l_stick_hor),
        50,   #clamp_int(l_stick_ver),
        50,   #clamp_int(r_stick_hor),
        50,   #clamp_int(r_stick_ver),
        80,   #clamp_int(l_trigger,0,200),
        90,   #clamp_int(r_trigger,0,200),
        5,    #int(setting1),
        4,    #int(setting2),
        beep)
    remote_control.write(controller_state)

    # Make sure to clean up when user stops program with center button
    # if button.center.is_pressed():
    #     break

    # Limit the sending rate of control packets to about 30/s
    time.sleep_ms(30)

# Clean up
remote_control.disconnect()
del(remote_control)
print("Disconnected")
raise SystemExit

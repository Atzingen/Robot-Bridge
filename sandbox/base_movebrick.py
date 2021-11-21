from mindstorms import MSHub, Motor, MotorPair, ColorSensor, DistanceSensor, App
from mindstorms.control import wait_for_seconds, wait_until, Timer
from mindstorms.operator import greater_than, greater_than_or_equal_to, less_than, less_than_or_equal_to, equal_to, not_equal_to
import math, time


# Create your objects here.
hub = MSHub()


# Write your program here.
hub.speaker.beep()

motor_pair = MotorPair('A', 'E')

motor_pair.start(0, speed=30)

time.sleep(1)

motor_pair.stop()
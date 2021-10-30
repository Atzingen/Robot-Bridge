from machine import Pin, ADC
from time import sleep

pot = ADC(Pin(34))
pot.atten(ADC.ATTN_11DB)       #Full range: 3.3v
btn = Pin(12, Pin.IN, Pin.PULL_UP)

while btn.value():
    pot_value = pot.read()
    print(pot_value)
    sleep(0.1)
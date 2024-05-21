# Read the voltage from a LiPo battery connected to a Raspberry Pi Pico via Pico Lipo SHIM
# and uses this reading to calculate how much charge is left in the battery.
# It then sends the battery voltage via the battery bluetooth.

from machine import ADC, Pin
import time



vsys = ADC(29)                      # reads the system input voltage
charging = Pin('WL_GPIO2', Pin.IN)          # reading GP24 tells us whether or not USB power is connected
conversion_factor = 3 * 3.3 / 65535

full_battery = 4.2                  # these are our reference voltages for a full/empty battery, in volts
empty_battery = 2.8                 # the values could vary by battery size/manufacturer so you might need to adjust them


while True:
    # convert the raw ADC read into a voltage, and then a percentage
    voltage = vsys.read_u16() * conversion_factor
    percentage = 100 * ((voltage - empty_battery) / (full_battery - empty_battery))
    if percentage > 100:
        percentage = 100.00

    # draw a green box for the battery level
    print(f'Battery percentage remaining {percentage}')
    
    if charging.value() == 1:         # if it's plugged into USB power...
        print("Charging!")
    else:                             # if not, display the battery stats
        print(f'Voltage {voltage}')


    time.sleep(0.5)
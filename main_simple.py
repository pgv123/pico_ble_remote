# Import necessary modules
from machine import UART, Pin 
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
import json


def save_config():
    """function to save the config dict to the JSON file"""
    with open("config.json", "w") as f:
        json.dump(config, f)

        
# load the config file from flash
with open("config.json") as f:
    config = json.load(f)

Namestr = config["BLEName"]
print (type(Namestr))
print("BLE Name: ", Namestr)




# Create a Bluetooth Low Energy (BLE) object
ble = bluetooth.BLE()

# Create an instance of the BLESimplePeripheral class with the BLE object
sp = BLESimplePeripheral(ble, Namestr)

# Create a Pin object for the onboard LED, configure it as an output
led = Pin("LED", Pin.OUT)

# Initialize the LED state to 0 (off)
led_state = 0

# Define a callback function to handle received data
def on_rx(data):
    print("Data received: ", data)  # Print the received data
    global led_state  # Access the global variable led_state
    if data[0:6] == b'230404':  # Check if the received data is the correct project
        led.value(not led_state)  # Toggle the LED state (on/off)
        led_state = 1 - led_state  # Update the LED state

# Start an infinite loop
while True:
    if sp.is_connected():  # Check if a BLE connection is established
        sp.on_write(on_rx)  # Set the callback function for data reception
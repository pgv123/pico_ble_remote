# Author: Renzo Mischianti
# Website: www.mischianti.org
#
# Description:
# This script demonstrates how to use the E32 LoRa module with MicroPython.
# Sending string
#
# Note: This code was written and tested using MicroPython on an ESP32 board.
#       It works with other boards, but you may need to change the UART pins.

import lora_e32     # import Logger, LoRaE32, Configuration
from machine import UART

from lora_e32_operation_constant import ResponseStatusCode

logger = Logger(True)

logger = logging.getLogger(__name__)

# Initialize the LoRaE32 module
uart1 = UART(1, baudrate=9600)
lora = LoRaE32('433T20D', uart1, m0_pin=21, m1_pin=22)
code = lora.begin()
print("Initialization: {}", ResponseStatusCode.get_description(code))
logger.info("In the Logger","but no useful info here")

# Set the configuration to default values and print the updated configuration to the console
# Not needed if already configured
# configuration_to_set = Configuration('433T20D')
# code, confSetted = lora.set_configuration(configuration_to_set)
# print("Set configuration: {}", ResponseStatusCode.get_description(code))

# Send a string message (transparent)
for i in range(100): 
    message = 'Hello, Peter!'
    code = lora.send_transparent_message(message)
    print(f"Send message: {message}", ResponseStatusCode.get_description(code))

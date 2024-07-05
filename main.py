import sys

import aioble
import bluetooth
from lora_e32 import Logger, LoRaE32, Configuration
from lora_e32_operation_constant import ResponseStatusCode
from machine import ADC, Pin, UART
import uasyncio as asyncio
from micropython import const
import struct

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

#Device Information
Company = "AusSport" # Limited Chars
Model = "Pico BLE" # to LORA Interface"
def uid():
    """ Return the unique id of the device as a string """
    return "{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}".format(
        *machine.unique_id())
Hardware = "1.0"
Software = "1.0.0.1"


MANUFACTURER_ID = const(0x02A29)
MODEL_NUMBER_ID = const(0x2A24)
SERIAL_NUMBER_ID = const(0x2A25)
HARDWARE_REVISION_ID = const(0x2A26)
BLE_VERSION_ID = const(0x2A28)

#button_a = Button(12)
#button_b = Button(13)
#button_x = Button(14)
#button_y = Button(15)

led = Pin("LED", Pin.OUT)

# Initialize the LoRaE32 module
uart1 = UART(1, baudrate=9600)
lora = LoRaE32('433T20D', uart1, m0_pin=21, m1_pin=22)
code = lora.begin()
print("Initialization: {}", ResponseStatusCode.get_description(code))

_DEVICE_INFO_UUID = bluetooth.UUID(0x180A) # Device Information
_GENERIC = bluetooth.UUID(0x1848)
_BATTERY_UUID = bluetooth.UUID(0x180F)
_ROBOT = bluetooth.UUID(0x1800)

#the Project Service and Characteristic
_PROJECT_UUID = bluetooth.UUID("116459e5-ad1a-4d85-9b9d-fc2e6cd6b3e0")

_PROJ_NUM_UUID = bluetooth.UUID("116459e6-ad1a-4d85-9b9d-fc2e6cd6b3e0")
_PROJ_KEEPALIVE_UUID = bluetooth.UUID("116459e7-ad1a-4d85-9b9d-fc2e6cd6b3e0")

#this is the generic Nordic Uart Service UUID, it supports two characteristics - TX and RX
_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")

#the UART characteristics
_TX_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
_RX_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

#the battery characteristic
_BATTERY = bluetooth.UUID(0x2A19)
                              
_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL = const(384)

ADV_INTERVAL_MS = 250_000

device_info = aioble.Service(_DEVICE_INFO_UUID)

project_info = aioble.Service(_PROJECT_UUID)



                              
connection = None

Project = "000000"


readproj = False
while (readproj == False):
    try:
        f1 = open('project.txt','r')
        Project = f1.read()
        readproj = True
    except:              #I think this means there is no such file
        f1 = open('project.txt','w')
        f1.write('000000')
        f1.close()
    

print (f'Project No: {Project}')

proj_characteristic = aioble.Characteristic(project_info, _PROJ_NUM_UUID, read=True, write=True, capture=True, initial=Project)
keepalive_characteristic = aioble.Characteristic(project_info, _PROJ_KEEPALIVE_UUID, write=True, capture=True, initial="Not OK")

print (f'Project Char: {proj_characteristic}')
print (f'Keep Alive Char: {proj_characteristic}')
# Create Characteristic for device info
aioble.Characteristic(device_info, bluetooth.UUID(MANUFACTURER_ID), read=True, initial=Company)
aioble.Characteristic(device_info, bluetooth.UUID(MODEL_NUMBER_ID), read=True, initial=Model)
aioble.Characteristic(device_info, bluetooth.UUID(SERIAL_NUMBER_ID), read=True, initial=uid())
aioble.Characteristic(device_info, bluetooth.UUID(HARDWARE_REVISION_ID), read=True, initial=Hardware) #sys.version)
aioble.Characteristic(device_info, bluetooth.UUID(BLE_VERSION_ID), read=True, initial=Software)


remote_service = aioble.Service(_GENERIC)
uart_service = aioble.Service(_UART_UUID)

#button_characteristic = aioble.Characteristic(
 #   remote_service, _BUTTON_UUID, read=True, notify=True)


_UART_RX = (    _RX_UUID,    _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,  )
_UART_TX = (    _TX_UUID,    _FLAG_READ | _FLAG_NOTIFY,   )


rx_characteristic = aioble.Characteristic(
    uart_service, _RX_UUID, write=True, notify=True, capture=True)

tx_characteristic = aioble.Characteristic(
    uart_service, _TX_UUID, read=True, notify=True)

#set up the battery service and characteristic
battery_info = aioble.Service(_BATTERY_UUID)

batt_level = aioble.Characteristic(battery_info, _BATTERY, read=True, notify=True)

print("Registering services")

aioble.register_services(uart_service, device_info, project_info, battery_info)

print("Out of Registering services")
connected = False

def measure_vsys():
    Pin(25, Pin.OUT, value=1)
    Pin(29, Pin.IN, pull=None)
    reading = ADC(3).read_u16() # * 9.9 / 2**16
    Pin(25, Pin.OUT, value=0, pull=Pin.PULL_DOWN)
    Pin(29, Pin.ALT, pull=Pin.PULL_DOWN, alt=7)
    return reading

async def peripheral_task():
    """ Task to handle peripheral """
    print('peripheral task started')
    global connected, connection, message, Project, count
    while True:
        connected = False
        async with await aioble.advertise(
            ADV_INTERVAL_MS,
            name="AusSport Sboard P" + Project,
            appearance=_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL,
            services=[_UART_UUID]
        ) as connection:
            print("Connection from, ", connection.device)
            connected = True
            print("connected")
            while connection.is_connected():
                count = +1
                if count > 3: #COUNT_MAX:
                    print("It's dead or it's not GameChanger at the other end!")
                    connected = False
                    alive = False
                else:                 
                    message = "AusSport P" + Project
                    tx_characteristic.write(message.encode('ascii'),send_update=True)
                    await asyncio.sleep_ms(5_000)   #
            await connection.disconnected()
            print("disconnected")

async def keepalive_task():
    global connected, connection, count
    print('keep alive task started')
    global read_char
    read_char = False
    count = 0
    while True:
        if connected == True:
           # print("Connected in RX")
            alive = True
        else:
           # print("Not Connected")
            alive = False
            count = 0
            await asyncio.sleep_ms(100)
            continue
    
        if alive == True:
             
            if keepalive_characteristic != None:
                try:
                    print("Waiting for Keep Alive...")
                    connection, keepalive = await keepalive_characteristic.written()
                    ret_char = keepalive.decode('ascii')
                    if keepalive.decode('ascii') == "OK":
                        count = 0       #go back to the start...it's alive!
                    await asyncio.sleep_ms(5000)
                        
                except TypeError:
                    print(f'something went wrong; remote disconnected?')
                    connected = False
                    alive = False
                    return
                except asyncio.TimeoutError:
                    print(f'something went wrong; timeout error?')
                    connected = False
                    alive = False
                    return
                except asyncio.GattError:
                    print(f'something went wrong; Gatt error - did the remote die?')
                    connected = False
                    alive = False
                    return


async def proj_task():
    global connected, connection, Project
    print('proj task started')
    global read_char
    read_char = False
    while True:
        if connected == True:
           # print("Connected in RX")
            alive = True
        else:
           # print("Not Connected")
            alive = False
            await asyncio.sleep_ms(100)
            continue
    
        if alive == True:
             
            if proj_characteristic != None:
                try:
                    #command = rx_characteristic(..., capture=True)
                    print("Waiting for any change in Project No...")
                    read_char = False
                    connection, rec_val = await proj_characteristic.written()  #rx_characteristic.write()
                    Project = rec_val.decode('ascii')
                    update_str = "Received New Project: " + Project
                    print (update_str)
                    tx_characteristic.write(update_str.encode('ascii'), send_update=True)
                    read_char = True
                    f1 = open('project.txt','w')
                    f1.write(Project)
                    f1.close()
                    await asyncio.sleep_ms(50)
                    
                        
                except TypeError:
                    print(f'something went wrong; remote disconnected?')
                    connected = False
                    alive = False
                    return
                except asyncio.TimeoutError:
                    print(f'something went wrong; timeout error?')
                    connected = False
                    alive = False
                    return
                except asyncio.GattError:
                    print(f'something went wrong; Gatt error - did the remote die?')
                    connected = False
                    alive = False
                    return
            await asyncio.sleep_ms(1)



async def rx_task():
    global connected, connection
    print('rx task started')
    global read_char
    read_char = False
    while True:
        if connected == True:
           # print("Connected in RX")
            alive = True
        else:
            print("Not Connected")
            alive = False
            await asyncio.sleep_ms(100)
            continue
    
        if alive == True:
             
            if rx_characteristic != None:
                try:
                    #command = rx_characteristic(..., capture=True)
                    print("Waiting for RX chars...")
                    read_char = False
                    connection, rec_val = await rx_characteristic.written()  #rx_characteristic.write()
                    Message = rec_val.decode('ascii')
                    print (f"Received: {Message}")
                    read_char = True
                    code = lora.send_transparent_message(Message)
                    print(f"Send Radio message: {Message}", ResponseStatusCode.get_description(code))
                    tx_characteristic.write(Message.encode('ascii'), send_update=True)
                    await asyncio.sleep_ms(50)
                    
                        
                except TypeError:
                    print(f'something went wrong; remote disconnected?')
                    connected = False
                    alive = False
                    return
                except asyncio.TimeoutError:
                    print(f'something went wrong; timeout error?')
                    connected = False
                    alive = False
                    return
                except asyncio.GattError:
                    print(f'something went wrong; Gatt error - did the remote die?')
                    connected = False
                    alive = False
                    return
            await asyncio.sleep_ms(1)
            
    # Helper to encode the voltage characteristic encoding (sint16).
def _encode_voltage(vc):
    return struct.pack("<h", int(vc))


async def read_voltage():
    print ('read voltage started')
    global connected
    
    toggle = True
    while True:
        charging = Pin('WL_GPIO2', Pin.IN)          # reading GP24 tells us whether or not USB power is connected
        conversion_factor = 3 * 3.3 / 65535

        full_battery = 4.2                  # these are our reference voltages for a full/empty battery, in volts
        empty_battery = 2.8                 # the values could vary by battery size/manufacturer so you might need to adjust them
        voltage = measure_vsys() * conversion_factor
        # convert the raw ADC read into a voltage, and then a percentage
        percentage = 100 * ((voltage - empty_battery) / (full_battery - empty_battery))
        if percentage > 100:
            percentage = 100.00


#        print(f'Battery percentage remaining {percentage}')
        percent = _encode_voltage(percentage)
        batt_level.write(percent, send_update=True)
    
        if charging.value() == 1:         # if it's plugged into USB power...
            print("Charging!")
        else:                             # if not, display the battery stats
            print(f'Voltage {voltage}')
        await asyncio.sleep_ms(5_000)



async def blink_task():
    """ Task to blink LED """
    print ('blink task started')
    global connected
    toggle = True
    while True:
        led.value(toggle)
        toggle = not toggle
        blink = 1000
        if connected:
            blink = 1000
        else:
           # print ("Not Connected")
            blink = 250
        await asyncio.sleep_ms(blink)

async def main():

    tasks = [
        asyncio.create_task(peripheral_task()),
        asyncio.create_task(blink_task()),
        asyncio.create_task(rx_task()),
        asyncio.create_task(proj_task()),
        asyncio.create_task(keepalive_task()),        
        asyncio.create_task(read_voltage())
    ]
    await asyncio.gather(*tasks)

asyncio.run(main())
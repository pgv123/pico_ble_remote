import sys
import aioble
#from libs.peripheral import advertise
import bluetooth
from lora_e32 import Logger, LoRaE32, print_configuration, Configuration
from lora_e32_operation_constant import ResponseStatusCode
from machine import ADC, Pin, UART
import uasyncio as asyncio
from micropython import const
import struct


#Costants and flags
_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

#Device Information
Company = "AusSport" # Limited Chars
Model = "Pico BLE" # to LORA Interface"

Hardware = "1.0"
Software = "1.0.0.1"


#UUIDs
#the Generic Device Info Service
_DEVICE_INFO_UUID = bluetooth.UUID(0x180A)
#Info Service Characteristics
MANUFACTURER_ID = const(0x02A29)
MODEL_NUMBER_ID = const(0x2A24)
SERIAL_NUMBER_ID = const(0x2A25)
HARDWARE_REVISION_ID = const(0x2A26)
BLE_VERSION_ID = const(0x2A28)
#the Generic Battery Service
_BATTERY_UUID = bluetooth.UUID(0x180F)
#the Battery Characteristic
_BATTERY = bluetooth.UUID(0x2A19)
#the Project Service
_PROJECT_UUID = bluetooth.UUID("116459e5-ad1a-4d85-9b9d-fc2e6cd6b3e0")
#the Project Characteristics
_PROJ_NUM_UUID = bluetooth.UUID("116459e6-ad1a-4d85-9b9d-fc2e6cd6b3e0")
_PROJ_KEEPALIVE_UUID = bluetooth.UUID("116459e7-ad1a-4d85-9b9d-fc2e6cd6b3e0")

#this is the generic Nordic Uart Service UUID
#_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
#the UART characteristics
#_TX_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
#_RX_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")

#purely for testing
_UART_UUID = bluetooth.UUID("5f908c2c-a6aa-4423-acb0-b260943a4275")
#the UART characteristics
_TX_UUID = bluetooth.UUID("5f908c2d-a6aa-4423-acb0-b260943a4275")
_RX_UUID = bluetooth.UUID("5f908c2e-a6aa-4423-acb0-b260943a4275")


_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL = const(384)

ADV_INTERVAL_MS = 250_000

MAX_COUNT = 6

#led = Pin("LED", Pin.OUT)
led = Pin(19, Pin.OUT)
# Initialize the LoRaE32 module
uart1 = UART(1, baudrate=9600)

lora = LoRaE32('433T20D', uart1, aux_pin=3, m0_pin=6, m1_pin=7)
code = lora.begin()
print("Initialization: {}", ResponseStatusCode.get_description(code))
code, configuration = lora.get_configuration()

print("Retrieve configuration: {}", ResponseStatusCode.get_description(code))

print_configuration(configuration)


print("Address H:", configuration.ADDH, " L:",configuration.ADDL," Channel: ",configuration.CHAN)

#Functions

#  Return the unique id of the device as a string to be used as Device Serial no.
def uid():
     return "{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}".format(
        *machine.unique_id())

#Get the battery voltage
def measure_vsys():
    Pin(25, Pin.OUT, value=1)
    Pin(29, Pin.IN, pull=None)
    reading = ADC(3).read_u16() # * 9.9 / 2**16
    Pin(25, Pin.OUT, value=0, pull=Pin.PULL_DOWN)
    Pin(29, Pin.ALT, pull=Pin.PULL_DOWN, alt=7)
    return reading                           

# Helper to encode the voltage characteristic encoding (sint16).
def _encode_voltage(vc):
    return struct.pack("<h", int(vc))

#Read project number from file or create it
readproj = False
while not readproj:
    try:
        with open('project.txt','r') as f:
            Project = f.readline().strip()
            Radio_Channel = int(f.readline().strip())
            Radio_Addr_High = int(f.readline().strip())
            Radio_Addr_Low = int(f.readline().strip())
            Radio_Programmed = int(f.readline().strip())       
            readproj = True
    except OSError:              #I think this means there is no such file
        with open('project.txt','w') as f:
            f.write('000000')
            Project = "000000"
            f.write('\n10')  # Default Radio Channel
            f.write('\n0')   # Default Radio Address High
            f.write('\n0')   # Default Radio Address Low
            f.write('\n0')  # Default Radio Programmed (0 = not programmed)
            Radio_Channel = 10
            Radio_Addr_High = 0
            Radio_Addr_Low = 0
            Radio_Programmed = 0

print (f'Project No: {Project}')
print (f'Radio Channel: {Radio_Channel}')
print (f'Radio Address High: {Radio_Addr_High}')
print (f'Radio Address Low: {Radio_Addr_Low}')
print (f'Radio Programmed: {Radio_Programmed}')

if Radio_Programmed == 0:
    print("Programming Radio")
    configuration.CHAN = Radio_Channel
    configuration.ADDH = Radio_Addr_High
    configuration.ADDL = Radio_Addr_Low
    code, confSetted = lora.set_configuration(configuration)
    print("Programming New Config! ", ResponseStatusCode.get_description(code))
    print_configuration(configuration)
    print_configuration(confSetted)
    Radio_Programmed = 1
    with open('project.txt','w') as f:
        f.write(Project)
        f.write('\n')
        f.write(str(Radio_Channel))
        f.write('\n')
        f.write(str(Radio_Addr_High))
        f.write('\n')
        f.write(str(Radio_Addr_Low))
        f.write('\n')
        f.write(str(Radio_Programmed))
        f.write('\n')
else:
    print("Radio already programmed")

# Services and Characteristics
device_info = aioble.Service(_DEVICE_INFO_UUID)
project_info = aioble.Service(_PROJECT_UUID)
uart_service = aioble.Service(_UART_UUID)
battery_info = aioble.Service(_BATTERY_UUID)

proj_characteristic = aioble.Characteristic(project_info, _PROJ_NUM_UUID, read=True, write=True, capture=True, initial=Project)
keepalive_characteristic = aioble.Characteristic(project_info, _PROJ_KEEPALIVE_UUID, write=True, write_no_response=True, capture=True, initial="Not OK")
rx_characteristic = aioble.Characteristic(uart_service, _RX_UUID, write=True, write_no_response=True, capture=True, initial="Test") #this is the sending to LORA characteristic so Gameaioble.Changer has to write to it
tx_characteristic = aioble.Characteristic(uart_service, _TX_UUID, read=True, notify=True) #this is the receiving from LORA characteristic so GameChanger has to read from it
batt_level = aioble.Characteristic(battery_info, _BATTERY, read=True, notify=True)

aioble.Characteristic(device_info, bluetooth.UUID(MANUFACTURER_ID), read=True, initial=Company)
aioble.Characteristic(device_info, bluetooth.UUID(MODEL_NUMBER_ID), read=True, initial=Model)
aioble.Characteristic(device_info, bluetooth.UUID(SERIAL_NUMBER_ID), read=True, initial=uid())
aioble.Characteristic(device_info, bluetooth.UUID(HARDWARE_REVISION_ID), read=True, initial=Hardware) #sys.version)
aioble.Characteristic(device_info, bluetooth.UUID(BLE_VERSION_ID), read=True, initial=Software)

#Register services
aioble.register_services(uart_service, device_info, project_info, battery_info)
#By writing a dummy value the buffer for that characteristic is set to the number of characters now set to 60
rx_characteristic.write("AusSport Scoreboards Messaging via BLE and Android Tablet   ")

#Global Variables
connected = False
connection = None

# Tasks
async def peripheral_task():
    print('peripheral task started')
    global connected, connection, message, Project, count_flag, count
    connected = False
    while not connected:
        print('Commence advertising!')
        count = 0
        async with await aioble.advertise(
            ADV_INTERVAL_MS,
            name="AusSport Sboard P" + Project,
            appearance=_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL,
            services=[_UART_UUID] #_BATTERY_UUID, _DEVICE_INFO_UUID, _PROJECT_UUID] can't use these as goes over length
        ) as connection:
            print("Connection from, ", connection.device)
            connected = True
            print("connected")
            count_flag = False #is only set by receiving the keepalive         
            #await connection.disconnected(timeout_ms=None)
            while (connection.is_connected() and count <= MAX_COUNT):
                #print('*')
                if count_flag:
                    count = count + 1
                await asyncio.sleep_ms(1000)
            else:
                print(f'disconnected with count: {count}')
                machine.reset()
                count = 0
                connected = False
                connection = None

async def keepalive_task():
    global connected, connection, count, count_flag
    print('keep alive task started')

    count = 0
    while True:
        if connected:
            alive = True
        else:
            alive = False
            count = 0
            await asyncio.sleep_ms(1000)
            continue
    
        if alive:        
            if keepalive_characteristic:
                try:
                    print("Waiting for Keep Alive...")
                    connection, keepalive = await keepalive_characteristic.written()
                    ret_char = keepalive.decode('ascii')
                    if ret_char == "OK":
                        count = 0       #go back to the start...it's alive!
                        count_flag = True
                        print(ret_char)
                        ret_char = ''
                        keepalive_characteristic.write(ret_char.encode('ascii'))
                    await asyncio.sleep_ms(5000)
                        
                except (TypeError, asyncio.TimeoutError, asyncio.GattError):
                    print(f'something went wrong; remote disconnected?')
                    connected = False
                    alive = False

async def proj_task():
    global connected, connection, Project
    print('proj task started')
    while True:
        if connected:
            alive = True
        else:
            alive = False
            await asyncio.sleep_ms(1000)
            continue
    
        if alive:
             
            if proj_characteristic:
                try:
                    print("Waiting for any change in Project No...")
                    connection, rec_val = await proj_characteristic.written()
                    Project = rec_val.decode('ascii')
                    update_str = "Received New Project: " + Project
                    print (update_str)
                    tx_characteristic.write(update_str.encode('ascii'), send_update=True)
                    with open('project.txt','w') as f:
                        f.write(Project)
                    await asyncio.sleep_ms(50)
                    
                except (TypeError, asyncio.TimeoutError, asyncio.GattError):
                    print(f'something went wrong; remote disconnected?')
                    connected = False
                    alive = False

async def rx_task():
    global connected, connection
    print('rx task started')
    while True:
        if connected:
            alive = True
        else:
            alive = False
            await asyncio.sleep_ms(1000)
            continue
    
        if alive:             
            try:
                print("Waiting for RX chars...")
                connection, rec_val = await rx_characteristic.written()  #rx_characteristic.write()
                RawMessage = rec_val.decode('ascii')
                print (f"Received: {repr(RawMessage)}")
                FirstChar = RawMessage[0]            
                Message = RawMessage[1:]
                print (f"First Char: {repr(FirstChar)}, Message: {repr(Message)}")
                if FirstChar == "T":
                    print ("inside T")
                    code = lora.send_transparent_message(Message)
                    print(f"Send Radio message: {repr(Message)}", ResponseStatusCode.get_description(code))
                 #  tx_characteristic.write(Message.encode('ascii'), send_update=True)
                elif FirstChar == "R":
                    code, configuration = lora.get_configuration()
                   #print_configuration(configuration)
                elif FirstChar == "C":
                    cH = int(Message)
                    if cH >= 0 and cH < 32:
                        code, configuration = lora.get_configuration()                        
                        configuration.CHAN = int(Message)
                        print(configuration.CHAN)
                        #print_configuration(configuration)
                    else:
                        print("Invalid Channel: ", Message)
                elif FirstChar == "A":
                    L_Mess = Message.split(",")
                    aH = int(L_Mess[0])
                    aL = int(L_Mess[1])
                    if aH >= 0 and aH < 256 and aL >= 0 and aL < 256:
                        code, configuration = lora.get_configuration()                        
                        print("New aH and aL: ", aH, aL)
                        configuration.ADDH = int(L_Mess[0])
                        configuration.ADDL = int(L_Mess[1])
                        print("New Address: ", configuration.ADDH, configuration.ADDL)
                        #print_configuration(configuration)
                    else:
                        print("Invalid Values for Address: ", Message)
                elif FirstChar == "P":
                    code, confSetted = lora.set_configuration(configuration)
                    print("Programming New Config! ", ResponseStatusCode.get_description(code))
                    #print_configuration(configuration)
                    #print_configuration(confSetted)
                else:
                    print("Got Rubbish!...ignoring this: ", Message)                              
                    await asyncio.sleep_ms(50)
                    
            except (TypeError, asyncio.TimeoutError, asyncio.GattError):
                print(f'something went wrong; remote disconnected?')
                connected = False
                alive = False
            
async def read_voltage():
    print ('read voltage started')
    global connected
    while True:
        charging = Pin('WL_GPIO2', Pin.IN)          # reading GP24 tells us whether or not USB power is connected
        conversion_factor = 3 * 3.3 / 65535
        full_battery = 4.2                  # these are our reference voltages for a full/empty battery, in volts
        empty_battery = 2.8                 # the values could vary by battery size/manufacturer so you might need to adjust them
        voltage = measure_vsys() * conversion_factor
        # convert the raw ADC read into a voltage, and then a percentage
        percentage = 100 * ((voltage - empty_battery) / (full_battery - empty_battery))
        percentage = min(max(percentage, 0), 100)
#        print(f'Battery percentage remaining {percentage}')
        percent = _encode_voltage(percentage)
        batt_level.write(percent, send_update=True)
    
        if charging.value() == 1:         # if it's plugged into USB power...
            print("Charging!")
        else:                             # if not, display the battery stats
            print(f'Voltage {voltage}')
        await asyncio.sleep_ms(5_000)


async def blink_task():
    print ('blink task started')
    global connected
    toggle = True
    while True:
        toggle = not toggle
        blink = 1500 if connected else 350
        led.value(toggle)
        await asyncio.sleep_ms(8)
        led.value(0)
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
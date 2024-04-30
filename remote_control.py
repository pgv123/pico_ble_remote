import sys

import aioble
import bluetooth
import machine
import uasyncio as asyncio
from micropython import const

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

def uid():
    """ Return the unique id of the device as a string """
    return "{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}".format(
        *machine.unique_id())

MANUFACTURER_ID = const(0x02A29)
MODEL_NUMBER_ID = const(0x2A24)
SERIAL_NUMBER_ID = const(0x2A25)
HARDWARE_REVISION_ID = const(0x2A26)
BLE_VERSION_ID = const(0x2A28)

#button_a = Button(12)
#button_b = Button(13)
#button_x = Button(14)
#button_y = Button(15)

led = machine.Pin("LED", machine.Pin.OUT)

_DEVICE_INFO_UUID = bluetooth.UUID(0x180A) # Device Information
_GENERIC = bluetooth.UUID(0x1848)
_BUTTON_UUID = bluetooth.UUID(0x2A6E)
_ROBOT = bluetooth.UUID(0x1800)

#this is the generic Nordic Uart Service UUID, it supports two characteristics - TX and RX
_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_TX_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
_RX_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
                              
_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL = const(384)

ADV_INTERVAL_MS = 250_000

device_info = aioble.Service(_DEVICE_INFO_UUID)
                              
connection = None

# Create Characteristic for device info
aioble.Characteristic(device_info, bluetooth.UUID(MANUFACTURER_ID), read=True, initial="AusSport")
aioble.Characteristic(device_info, bluetooth.UUID(MODEL_NUMBER_ID), read=True, initial="1.0")
aioble.Characteristic(device_info, bluetooth.UUID(SERIAL_NUMBER_ID), read=True, initial=uid())
aioble.Characteristic(device_info, bluetooth.UUID(HARDWARE_REVISION_ID), read=True, initial="1.0") #sys.version)
aioble.Characteristic(device_info, bluetooth.UUID(BLE_VERSION_ID), read=True, initial="1.0")

remote_service = aioble.Service(_GENERIC)
uart_service = aioble.Service(_UART_UUID)

#button_characteristic = aioble.Characteristic(
 #   remote_service, _BUTTON_UUID, read=True, notify=True)


_UART_RX = (    _RX_UUID,    _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,  )
_UART_TX = (    _TX_UUID,    _FLAG_READ | _FLAG_NOTIFY,   )


rx_characteristic = aioble.Characteristic(
    uart_service, _RX_UUID, write=True, notify=False, capture=True)

tx_characteristic = aioble.Characteristic(
    uart_service, _TX_UUID, read=True, notify=True)

print("Registering services")

aioble.register_services(uart_service) #, device_info)

connected = False

async def remote_task():
    """ Task to handle remote control """
    print("remote task started")
    while True:
        if not connected:
            print("Not Connected")
            await asyncio.sleep_ms(1000)
            continue

        await asyncio.sleep_ms(100)

async def peripheral_task():
    """ Task to handle peripheral """
    print('peripheral task started')
    global connected, connection
    while True:
        connected = False
        async with await aioble.advertise(
            ADV_INTERVAL_MS,
            name="AusSport Scoreboardssss",
            appearance=_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL,
            services=[_UART_UUID]
        ) as connection:
            print("Connection from, ", connection.device)
            connected = True
            print("connected {connected}")
            await connection.disconnected(timeout_ms=None)
            print("disconnected")

async def rx_task():
    global connected, connection
    print('rx task started')
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
                await rx_characteristic.written()
                try:
                    
                    print("Trying for written in RX")
                    rec_val = rx_characteristic.read()  
                    print (f"Command: {rec_val}")
                    if rec_val == b'a':
                        print("a button pressed")
                    elif rec_val == b'b':
                        print("b button pressed")
                    elif rec_val == b'x':
                        print("x button pressed")
                    elif rec_val == b'y':
                        print("y button pressed")
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
                except asyncio.CancelledError:
                    print(f'Connection Cancelled')
                    connected = False
                    alive = False
                    return
        
        await connection.disconnected()
        print("disconnected")
        alive = False
                    
        await asyncio.sleep_ms(1)



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
 #       asyncio.create_task(remote_task()),
        asyncio.create_task(blink_task()),
        asyncio.create_task(rx_task()),
    ]
    await asyncio.gather(*tasks)

asyncio.run(main())
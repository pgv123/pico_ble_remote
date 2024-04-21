# June 2023
# Bluetooth cores specification versio 5.4 (0x0D)
# Bluetooth Remote Control
# Kevin McAleer
# KevsRobot.com

import aioble
import bluetooth
import machine
import uasyncio as asyncio

# Bluetooth UUIDS can be found online at https://www.bluetooth.com/specifications/gatt/services/
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

_DEVICE_INFO_UUID = bluetooth.UUID(0x180A) # Device Information

#these UUIDs were generated using uuidgenerator.net
#the UART service and it's two characteristics - TX and RX
_UART_UUID = bluetooth.UUID("96cc48d1-2dac-49eb-b063-b15692349b8a")
_TX_UUID = bluetooth.UUID("e1f8cfaa-9c2d-493e-83b1-a0dc5a7850bc")
_RX_UUID = bluetooth.UUID("49dacc47-3b9a-464c-8899-9ffb90785c28")

_BLE_APPEARANCE_GENERIC_REMOTE_CONTROL = const(384)

led = machine.Pin("LED", machine.Pin.OUT)
connected = False
alive = False

ADV_INTERVAL_MS = 250_000

device_info = aioble.Service(_DEVICE_INFO_UUID)
                              
connection = None

# Create Characteristic for device info
aioble.Characteristic(device_info, bluetooth.UUID(MANUFACTURER_ID), read=True, initial="AusSport")
aioble.Characteristic(device_info, bluetooth.UUID(MODEL_NUMBER_ID), read=True, initial="1.0")
aioble.Characteristic(device_info, bluetooth.UUID(SERIAL_NUMBER_ID), read=True, initial=uid())
aioble.Characteristic(device_info, bluetooth.UUID(HARDWARE_REVISION_ID), read=True, initial=sys.version)
aioble.Characteristic(device_info, bluetooth.UUID(BLE_VERSION_ID), read=True, initial="1.0")

remote_service = aioble.Service(_GENERIC)
uart_service = aioble.Service(_UART_UUID)

button_characteristic = aioble.Characteristic(
    remote_service, _BUTTON_UUID, read=True, notify=True)



_UART_TX = (    _TX_UUID,    _FLAG_READ | _FLAG_NOTIFY,   )
_UART_RX = (    _RX_UUID,    _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,  )

rx_characteristic = aioble.Characteristic(
    uart_service, _RX_UUID, write=True, notify=False)

tx_characteristic = aioble.Characteristic(
    uart_service, _TX_UUID, read=True, notify=True)

print("Registering services")

aioble.register_services(uart_service, device_info)

connected = False

async def remote_task():
    """ Task to handle remote control """

    while True:
        if not connected:
            print("Not Connected")
            await asyncio.sleep_ms(1000)
            continue

        await asyncio.sleep_ms(10)


async def blink_task():
    """ Blink the LED on and off every second """
    
    toggle = True
    
    while True and alive:
        led.value(toggle)
        toggle = not toggle
        # print(f'blink {toggle}, connected: {connected}')
        if connected:
            blink = 1000
        else:
            blink = 250
        await asyncio.sleep_ms(blink)

async def peripheral_task():
    print('starting peripheral task')
    global connected
    connected = False
    device = await find_connection()
    if not device:
        print("Cannot find a connection")
        return
    try:
        print("Connecting to", device)
        connection = await device.connect()
        
    except asyncio.TimeoutError:
        print("Timeout during connection")
        return
      
    async with connection:
        print("Connected")
        connected = True
        alive = True
        while True and alive:
            try:
                robot_service = await connection.service(_REMOTE_UUID)
                print(robot_service)
                control_characteristic = await robot_service.characteristic(_REMOTE_CHARACTERISTICS_UUID)
                print(control_characteristic)
            except asyncio.TimeoutError:
                print("Timeout discovering services/characteristics")
                return
            
            while True:
                if control_characteristic == None:
                    print('no characteristic')
                    await asyncio.sleep_ms(10)
                    return
                
                if control_characteristic != None:
                    try:
                        command = await control_characteristic.read()

                        if command == b'a':
                            print("a button pressed")
                        elif command == b'b':
                            print("b button pressed")
                        elif command == b'x':
                            print("x button pressed")
                        elif command == b'y':
                            print("y button pressed")
                        await asyncio.sleep_ms(1)
                        
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
                

async def main():
    tasks = []
    tasks = [
        asyncio.create_task(blink_task()),
        asyncio.create_task(peripheral_task()),
    ]
    await asyncio.gather(*tasks)
    
while True:
    asyncio.run(main())
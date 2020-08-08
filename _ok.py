# Synchronous proxy stuff ---------------------------------------------------- #
import socket

def _comm(request, host=('127.0.0.1', 4292)):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(host)
    s.settimeout(10)
    s.send(request)
    r = s.recv(1024)
    code, _, response = r.partition(b' ')
    if code == b'ERROR':
        raise OKProxyError(response)
    elif code == b'SUCCESS':
        return response

class OKProxyError(Exception):
    def __init__(self, response):
        super().__init__(response.decode())

class OKProxy(object):
    def __init__(self, host):
        r = _comm('START _ok'.encode(), host)
        self._host = host

    def okCFrontPanel(self):
        """ This class is the workhorse of the FrontPanel API. 
        
        It's methods are organized into three main groups: Device Interaction, 
        Device Configuration, and FPGA Communication. In a typical application, 
        your software will perform the following steps:
        
        1. Create an instance of okCFrontPanel.
        2. Using the Device Interaction methods, find an appropriate XEM with which 
        to communicate and open that device.
        3. Configure the device PLL (for devices with an on-board PLL).
        4. Download a configuration file to the FPGA using ConfigureFPGA(...).
        5. Perform any application-specific communication with the FPGA using the 
        FPGA Communication methods.    
        """
        return okFrontPanelProxy(self._host)

    def okCFrontPanelDevices(self, realm=''):
        """ Enumerates all the devices available in the given realm. 
    
        The realm of the devices represented by this object. By default, i.e. if
        the value of this argument is an empty string, the realm specified by 
        the okFP_REALM environment variable is used or, if this variable is not 
        defined, the "local" realm.
        """
        return okCFrontPanelDevicesProxy(self._host, realm)

class okCFrontPanelDevicesProxy(object):
    """ Enumerates all the devices available in the given realm. 
   
    The realm of the devices represented by this object. By default, i.e. if 
    the value of this argument is an empty string, the realm specified by 
    the okFP_REALM environment variable is used or, if this variable is not 
    defined, the "local" realm.
    """
    def __init__(self, host, realm=''):
        self._host = host
        self._realm = realm

    def GetCount(self):
        """ Returns the number of available devices, possibly 0. """
        r = _comm(f'COMM _ok GetCount'.encode(), self._host)
        return int.from_bytes(r, 'big')

    def GetSerial(self, num=None):
        """ Returns the serial number of the given device, possibly empty if the 
        index is invalid."""
        r = _comm(f'COMM _ok GetSerial {num}'.encode(), self._host)
        return r.decode()

    def Open(self, serial=''):
        """ Opens the device with the given serial number, first one by default. 
        
        Returns an empty pointer if there is no such device (or no devices at 
        all if the serial is empty).
        """
        r = _comm(f'COMM _ok Open {serial}'.encode())
        serial = r.decode()
        return okFrontPanelProxy(self._host, serial)

class okFrontPanelProxy(object):
    """ This class is the workhorse of the FrontPanel API. 
    
    It's methods are organized into three main groups: Device Interaction, 
    Device Configuration, and FPGA Communication. In a typical application, 
    your software will perform the following steps:
    
    1. Create an instance of okCFrontPanel.
    2. Using the Device Interaction methods, find an appropriate XEM with which 
    to communicate and open that device.
    3. Configure the device PLL (for devices with an on-board PLL).
    4. Download a configuration file to the FPGA using ConfigureFPGA(...).
    5. Perform any application-specific communication with the FPGA using the 
    FPGA Communication methods.    
    """
    def __init__(self, host, serial=None):
        self._host = host
        self._serial = serial

    def Close(self):
        """ Close the device.
    
        This method can be used to close the device to release the corresponding 
        device at the system level, e.g. to allow another process to use it, 
        without destroying this object itself but keeping it to be reopened later.
        """
        _comm(f'COMM _ok Close {self._serial}'.encode(), self._host)

    def ConfigureFPGA(self, strFilename):
        """ Download an FPGA configuration from a file.
        
        Args:
            strFilename	(str): A string containing the filename of the 
                configuration file.
        """
        r = _comm(f'COMM _ok ConfigureFPGA {self._serial} {strFilename}'.encode(), self._host)
        return int.from_bytes(r, 'big')

    def GetSerialNumber(self):
        r = _comm(f'_ok GetSerialNumber {self._serial}'.encode(), self._host)
        return r.decode()
    
    def GetWireInValue(self, epAddr):
        """ Gets the value of a particular Wire In from the internal wire data 
        structure.

        Args:
            epAddr (int): The WireIn address to query.
        """
        r = _comm(f'COMM _ok GetWireInValue {self._serial} {epAddr}'.encode(), self._host)
        return int.from_bytes(r, 'big')
    
    def GetWireOutValue(self, epAddr):
        """ Gets the value of a particular Wire Out from the internal wire data 
        structure.

        Args:
            epAddr (int): The WireOut address to query.
        """
        r = _comm(f'COMM _ok GetWireOutValue {self._serial} {epAddr}'.encode(), self._host)
        return int.from_bytes(r, 'big')
    
    def IsTriggered(self, epAddr, mask):
        """ Returns true if the trigger has been triggered.

        This method provides a way to find out if a particular bit (or bits) on 
        a particular TriggerOut endpoint has triggered since the last call to 
        UpdateTriggerOuts().

        Args:
            epAddr (int): The TriggerOut address to query.
            mask (int): A mask to apply to the trigger value.
        """
        r = _comm(f'COMM _ok IsTriggered {self._serial} {epAddr} {mask}'.encode(), self._host)
        return bool(int.from_bytes(r, 'big'))

    def SetWireInValue(self, epAddr, val, mask=0xffffffff):
        """ Sets a wire value in the internal wire data structure.

        WireIn endpoint values are stored internally and updated when necessary 
        by calling UpdateWireIns(). The values are updated on a per-endpoint 
        basis by calling this method. In addition, specific bits may be updated 
        independent of other bits within an endpoint by using the optional mask.

        Args:
            epAddr (int): The address of the WireIn endpoint to update.
            val (int): The new value of the WireIn.
            mask (int): A mask to apply to the new value
        """
        _comm(f'COMM _ok SetWireInValue {self._serial} {epAddr} {val} {mask}'.encode(), self._host)

    def UpdateTriggerOuts(self):
        """ Reads Trigger Out endpoints. 
        
        This method is called to query the XEM to determine if any TriggerOuts 
        have been activated since the last call.
        """
        _comm(f'COMM _ok UpdateTriggerOuts {self._serial}'.encode(), self._host)

    def UpdateWireIns(self):
        """ Transfers current Wire In values to the FPGA.

        This method is called after all WireIn values have been updated using 
        SetWireInValue(). The latter call merely updates the values held within 
        a data structure inside the class. This method actually commits the 
        changes to the XEM simultaneously so that all wires will be updated at 
        the same time.
        """
        _comm(f'COMM _ok UpdateTriggerOuts {self._serial}'.encode(), self._host)
    
    def UpdateWireOuts(self):
        """ Transfers current Wire Out values from the FPGA.

        This method is called to request the current state of all WireOut values
        from the XEM. All wire outs are captured and read at the same time.
        """
        _comm(f'COMM _ok UpdateWireOuts {self._serial}'.encode(), self._host)

    def WriteToPipeIn(self, epAddr, data):
        """ Writes a block to a Pipe In endpoint.

        Args:
            epAddr (int): The address of the destination Pipe In.
            data (bytearray): Data to be transferred
        """ 
        _comm(f'COMM _ok WriteToPipeIn {self._serial} {epAddr} '.encode() + data, self._host)

# Synchronous server stuff --------------------------------------------------- #
import ok
import json

devices = ok.okCFrontPanelDevices()
xem = {}


def handle_request_sync(request):
    member, _, args = request.partition(b' ')

    if member == b'GetCount':
        count = devices.GetCount()
        logging.info(f'{member}: {count}')
        return count.to_bytes(1, 'big')
    elif member == b'GetSerial':
        num = args.decode()
        serial = devices.GetSerial(num)
        logging.info(f'{member}: {serial}')
        return serial.encode()
    elif member == b'Open':
        serial = args.decode()
        if serial != '':
            _xem = devices.Open(serial)
            xem[serial] = _xem
            logging.info(f'{member}: {serial}')
            return serial.encode()
        else:
            _xem = devices.Open()
            logging.info(f'{_xem}')
            serial = _xem.GetSerialNumber()
            xem[serial] = _xem
            logging.info(f'{member}: {serial}')
            return serial.encode()
    elif member == b'Close':
        serial = args.decode()
        xem[serial].Close()
        logging.info(f'{member}: ')
        return b''
    elif member == b'ConfigureFPGA':
        serial, _, strFilename = args.decode().partition(' ')
        response = xem[serial].ConfigureFpga(strFilename)
        logging.info(f'{member}: {response}')
    elif member == b'GetSerialNumber':
        serial = args.decode()
        serial = xem[serial].GetSerialNumber()
        logging.info(f'{member}: {serial}')
        return serial.encode()
    elif member == b'GetWireInValue':
        serial, epAddr = args.decode().split(' ')
        response = xem[serial].GetWireInValue(epAddr)
        logging.info(f'{member}: {response}')
    elif member == b'GetWireInValue':
        serial, epAddr = args.split(' ')
        response = xem[serial].GetWireInValue(epAddr)
        logging.info(f'{member}: {response}')
    elif member == b'GetWireOutValue':
        serial, epAddr = args.split(' ')
        response = xem[serial].GetWireOutValue(epAddr)
        logging.info(f'{member}: {response}')
    elif member == b'IsTriggered':
        serial, epAddr, mask = args.split(' ')
        response = xem[serial].IsTriggered(epAddr, mask)
        logging.info(f'{member}: {response}')
    elif member == b'SetWireInValue':
        serial, epAddr, val, mask = args.split(' ')
        response = xem[serial].SetWireInValue(epAddr, val, mask)
        logging.info(f'{member}: {response}')
    elif member == b'UpdateTriggerOuts':
        serial = args
        response = xem[serial].UpdateTriggerOuts()
        logging.info(f'{member}: {response}')
    elif member == b'UpdateWireIns':
        serial = args
        response = xem[serial].UpdateWireIns(epAddr, val, mask)
        logging.info(f'{member}: {response}')
    elif member == b'UpdateWireOuts':
        serial = args
        response = xem[serial].UpdateWireOuts()
        logging.info(f'{member}: {response}')
    elif member == b'WriteToPipeIn':
        x, _, data = args.rpartition(b' ')
        serial, epAddr = x.decode().split(' ')
        response = xem[serial].WriteToPipeIn(epAddr, data)
        logging.info(f'{member}: {response}')

# Asynchronous server stuff -------------------------------------------------- #
if __name__ == '__main__':
    import asyncio
    import logging
    import os
    import sys
    
    async def handle_request(reader, writer):
        request = await reader.read(1024)
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(None, handle_request_sync, request)
            writer.write(b'SUCCESS ' + response)
            await writer.drain()
        except Exception as e:
            writer.write(b'ERROR ' + str(e).encode())
            await writer.drain()
            logging.exception('handle request')
            
    async def main():
        server = await asyncio.start_server(handle_request, 'localhost', 0)
        port = str(server.sockets[0].getsockname()[1])
        reader, writer = await asyncio.open_connection('localhost', 4292)
        logging.debug(modulepath)
        writer.write(f'PORT {modulename} {port}'.encode())
        await writer.drain()
        async with server:
            await server.serve_forever()
    
    modulepath = os.path.realpath(__file__)
    modulename = os.path.basename(modulepath).strip('.py')
    logging.basicConfig(filename=modulepath.replace('.py', '.log'), level=logging.DEBUG, 
                        format='%(message)s')
    asyncio.run(main())

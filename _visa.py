# Synchronous proxy stuff ---------------------------------------------------- #
import json
import socket

def _comm(data, host=('127.0.0.1', 4292)):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(host)
    s.settimeout(10)
    s.send(data)
    r = s.recv(1024)
    code, _, response = r.partition(b' ')
    if code == b'ERROR':
        raise RemoteError(response)
    elif code == b'SUCCESS':
        return response

class RemoteError(Exception):
    def __init__(self, response):
        super().__init__(response.decode())


class VisaProxy(object):
    def __init__(self, host=('localhost', 4292)):
        self._host = host
        r = _comm('START _visa'.encode(), self._host)

    def ResourceManager(self):
        return ResourceManagerProxy(self._host)


class ResourceManagerProxy(object):
    def __init__(self, host):
        self._host = host

    def list_resources(self, query='?*::INSTR'):
        """ Return a tuple of all connected devices matching query.
        
        Parameters:
            query (str) : VISA Resource Regular Expression syntax 
        Returns:
            (tuple) connected devices matching query
        """
        print(1)
        r = _comm(f'COMM _visa list_resources {query}'.encode(), self._host)
        print(2)
        return json.loads(r.decode())

    def open_resource(self, resource_name, open_timeout=0, **kwargs):
        """ Return an instrument for the resource name.

        Parameters: 
            resource_name (str): Name or alias of the resource to open.
            open_timeout (int, optional): If the access_mode parameter 
                requests a lock, then this parameter specifies the absolute 
                time period (in milliseconds) that the resource waits to get 
                unlocked before this operation returns an error, by default 
                constants.VI_TMO_IMMEDIATE.
            kwargs (Any) – Keyword arguments to be used to change instrument 
            attributes after construction.
        Returns:    
            Subclass of Resource matching the resource.
        """
        request = (resource_name, open_timeout, kwargs)
        r = _comm(f'COMM _visa open_resource {json.dumps(request)}'.encode(),
                  self._host)
        if 'GPIB' in resource_name:
            return GPIBInstrumentProxy(self._host, resource_name)
        else:
            raise VisaProxyError('resource type not supported :(')


class GPIBInstrumentProxy(object):
    def __init__(self, host, resource_name, **kwargs):
        self._host = host
        self._timeout = 3000
        self.resource_name = resource_name

    @property
    def _open_resource_kwargs(self):
        return {
            'timeout': self._timeout,
        }

    def control_ren(self, mode):
        """ Controls the state of the GPIB Remote Enable (REN) interface line.

        The remote/local state of the device can also be controlled optionally.
        Corresponds to viGpibControlREN function of the VISA library.

        Parameters: 
            mode (constants.RENLineOperation) - Specifies the state of the REN 
                line and optionally the device remote/local state.
        Returns:    
            Return value of the library call.
        """
        request = (self.resource_name, self._open_resource_kwargs, mode)
        r = _comm(f'COMM _visa control_ren {json.dumps(request)}'.encode(),
                  self._host)
        return int.from_bytes(r, 'big')

    def query(self, message, delay=None):
        """A combination of write(message) and read()

        Parameters:
            message (str): the message to send.
            delay (float): delay in seconds between write and read operations.
                if None, defaults to self.query_delay
        Returns:
            (str) the answer from the device.
        """
        request = (self.resource_name, self._open_resource_kwargs, message,
                   delay)
        r = _comm(f'COMM _visa query {json.dumps(request)}'.encode(),
                  self._host)
        return r.decode()

    def read(self, termination=None, encoding=None):
        """Read a string from the device.

        Reading stops when the device stops sending (e.g. by setting appropriate 
        bus lines), or the termination characters sequence was detected.
        Attention: Only the last character of the termination characters is 
        really used to stop reading, however, the whole sequence is compared to 
        the ending of the read string message. If they don't match, a warning is 
        issued.

        All line-ending characters are stripped from the end of the string.
        Parameters:
            termination (str): characters at which to stop reading
            encoding (str): encoding used for read operation
        Returns:
            (str) output from device
        """
        request = (self.resource_name, self._open_resource_kwargs, termination,
                   encoding)
        r = _comm(f'COMM _visa read {json.dumps(request)}'.encode(),
                  self._host)
        return r.decode()

    @property
    def timeout(self):
        """ The timeout in milliseconds for all resource I/O operations. """
        request = (self.resource_name, self._open_resource_kwargs)
        r = _comm(f'COMM _visa timeout_getattr {json.dumps(request)}'.encode(),
                  self._host)
        return int.from_bytes(r, 'big')

    @timeout.setter
    def timeout(self, timeout):
        """ The timeout in milliseconds for all resource I/O operations. """
        request = (self.resource_name, self._open_resource_kwargs, timeout)
        _comm(f'COMM _visa timeout_setattr {json.dumps(request)}'.encode(),
              self._host)
        self._timeout = timeout

    def write(self, message, termination=None, encoding=None):
        """ Write a string message to the device.

        The write_termination is always appended to it.

        Parameters:
            message (str): the message to be sent.
            termination (str): termination chars to be appended to message.
            encoding (str): byte encoding for message
        Returns:
            (int) number of bytes written
        """
        request = (self.resource_name, self._open_resource_kwargs, message,
                   termination, encoding)
        r = _comm(f'COMM _visa write {json.dumps(request)}'.encode(),
                  self._host)
        return int.from_bytes(r, 'big')

# Synchronous server stuff --------------------------------------------------- #
import visa
import json

rm = visa.ResourceManager()

def handle_request_sync(request):
    member, _, parameters = request.partition(b' ')

    logging.debug(0)
    if member == b'list_resources':
        query = parameters.decode()
        resources = rm.list_resources(query)
        logging.info(f'{member}: {resources}')
        return json.dumps(resources).encode()
    elif member == b'open_resource':
        resource_name, open_timeout, kwargs = json.loads(parameters.decode())
        inst = rm.open_resource(resource_name, open_timeout=open_timeout, 
                                **kwargs)
        logging.info(f'{member}: {inst}')
        return b''
    elif member == b'control_ren':
        resource_name, open_resource_kwargs, control_ren_kwargs = json.loads(parameters.decode())
        inst = rm.open_resource(resource_name, **open_resource_kwargs)
        response = json.dumps(inst.control_ren(**open_resource_kwargs))
    elif member == b'read':
        resource_name, open_resource_kwargs, termination, encoding = json.loads(parameters.decode())
        inst = rm.open_resource(resource_name, **open_resource_kwargs)
        response = inst.read(termination, encoding)
        logging.info(f'{member}: {response}')
        return response.encode()
    elif member == b'timeout_getattr':
        resource_name, open_resource_kwargs = json.loads(parameters.decode())
        inst = rm.open_resource(resource_name, **open_resource_kwargs)
        timeout = inst.timeout
        logging.info(f'{member}: {timeout}')
        return timeout.to_bytes(2, 'big')
    elif member == b'timeout_setattr':
        resource_name, open_resource_kwargs, timeout = json.loads(parameters.decode())
        inst = rm.open_resource(resource_name, **open_resource_kwargs)
        inst.timeout = timeout
    elif member == b'query':
        resource_name, open_resource_kwargs, message, delay = json.loads(parameters.decode())
        inst = rm.open_resource(resource_name, **open_resource_kwargs)
        response = inst.query(message, delay)
        logging.info(f'{member}: {response}')
        return response.encode()
    elif member == b'write':
        resource_name, open_resource_kwargs, message, termination, encoding = json.loads(parameters)
        inst = rm.open_resource(resource_name, **open_resource_kwargs)
        num_bytes = inst.write(message, termination, encoding)
        return num_bytes[0].to_bytes(4, 'big')

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

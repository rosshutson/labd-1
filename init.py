import asyncio
import contextvars
import logging
import os
import pathlib
import re
import time

PARENTDIR = os.path.dirname(os.path.realpath(__file__))
FORMAT = '%(asctime)s|%(levelname)-7s|%(message)s'
DATEFMT = '%H:%M:%S'
logging.basicConfig(filename=f'{os.path.join(PARENTDIR, "init.log")}',
                    level=logging.INFO,
                    format=FORMAT,
                    datefmt=DATEFMT)

processes = {}
ports = {}
events = {}


def consume(data):
    parts = data.partition(b' ')
    return parts[0].decode(), parts[2]

async def handle_request(reader, writer):
    in_ = await reader.read(1024)
    target, request = consume(in_)
    logging.debug(1)

    if target.upper() == 'START':
        target, request = consume(request)
        if target in processes:
            writer.write(b' ')
            await writer.drain()
        else:
            events[target] = asyncio.Event()
            cmd = f'python {os.path.join(PARENTDIR, target + ".py")} {request}'
            process = await asyncio.create_subprocess_shell(cmd)
            await events[target].wait()
            processes[target] = process
            writer.write(b' ')
            await writer.drain()
    elif target.upper() == 'STOP':
        await handle_stop_request(reader, writer, request)
        processes[target].terminate()
        await processes[target].wait()
        writer.write(b' ')
        await writer.drain()
    elif target.upper() == 'PORT':
        target, request = consume(request)
        if request:
            ports[target] = int(request)
        writer.write(str(ports[target]).encode())
        await writer.drain()
        events[target].set()
    elif target.upper() == 'COMM':
        logging.debug(-1)
        target, request = consume(request)
        logging.debug(-2)
        preader, pwriter = await asyncio.open_connection(
            'localhost', ports[target])
        logging.debug(-3)
        pwriter.write(request)
        logging.debug(-4)
        await pwriter.drain()
        logging.debug(-5)
        response = await preader.read(1024)
        logging.debug(-6)
        if response.find(b'ERROR ') != -1:
            message = target.ljust(
                7, ' ') + '|' + response.strip(b'ERROR ').decode()
            message = message.replace('\n', '\n' + time.strftime("%H:%M:%S") + f'|ERROR  |{target: <7}|')
            logging.error(message)
        logging.debug(-7)
        writer.write(response)
        await writer.drain()
        logging.debug(-8)


async def main():
    server = await asyncio.start_server(handle_request, '0.0.0.0', 4292)
    async with server:
        await server.serve_forever()


asyncio.run(main(), debug=False)

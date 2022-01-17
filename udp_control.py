from __future__ import division
import time
from thread import *
from threading import Thread
import math
import evdev
from evdev import ecodes
import socket
import datetime
from hs5645mg_servo_sdk.hs5645mg_servo_controller import HS5645MGServoController

servo_controller = HS5645MGServoController()
servo_controller.start()

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# TCP variables
_host_ip = get_ip()
_host_port = 1000
_connected = True
_first_init = True
_try_reconnect = True
_close_signal = False
_logger = None
_keep_listening_touch_events = False
_touch_controller_dev = None
_last_ball_position_reading = (0, 0)
send_position = True
data = None
_addr = None
def _touch_events_listening_thread_func():
    global _touch_controller_dev,_keep_listening_touch_events,_last_ball_position_reading
    if _logger is not None:
        _logger.debug("Starting listening to touch events.")
    while _keep_listening_touch_events:
        # This while will run on a different thread.
        try:
            event = _touch_controller_dev.read_one()
            if event is not None:
                if event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_X:
                        _last_ball_position_reading = (event.value, _last_ball_position_reading[1])
                    if event.code == ecodes.ABS_Y:
                        _last_ball_position_reading = (_last_ball_position_reading[0], event.value)
                if event.type == ecodes.EV_KEY:
                    if event.value == 1:
                        ball_contact = True
                    else:
                        ball_contact = False
            else:
                time.sleep(0.001)  # If there is no change from last loop, sleep 1ms
        except OSError,e:
            pass
    if _logger is not None:
        _logger.debug("Stopped listening to touch events.")

def start_listening_touch_events():
    global _touch_controller_dev,_keep_listening_touch_events
    if _logger is not None:
        _logger.info("Touch screen searching...")
    _touch_controller_dev = find_touch_controller_dev()
    if _logger is not None:
        _logger.info("Touch screen found!")
    _keep_listening_touch_events = True
    if _logger is not None:
        _logger.info("Touch screen thread starting...")
    # Start touch panel thread
    _touch_events_listening_thread = Thread(target=_touch_events_listening_thread_func)
    _touch_events_listening_thread.start()
    if _logger is not None:
        _logger.info("Touch screen thread started!")

def find_touch_controller_dev():
    TOUCH_CONTROLLER_NAME = "eGalax Inc."

    touch_controller_device = None
    # Initialize touch panel device
    devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
    for device in devices:
        if TOUCH_CONTROLLER_NAME in device.name:
            touch_controller_device = device
            print(device.name)
    return touch_controller_device

def get_ball_position_in_raw(): # To read position from outside of class in raw format
    return _last_ball_position_reading

def tcp_start():
    print("Starting TCP Server")
    global _connected, _first_init, _try_reconnect, conn,send_position,_close_signal,data,addr
    try:
        while True:
            if _close_signal:
                break
            if not _connected and not _close_signal:

                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind((_host_ip, _host_port))
                print("Socket bind completed")
                if s:
                    _connected = True
                    time.sleep(1)
                    while not data=="Start":
                        data, addr = s.recvfrom(5)
                        if data == "Start":
                            print(addr)
                            start_new_thread(receiver, (s,addr,))
                        time.sleep(0.001)
            time.sleep(1)
    except socket.error as msg:
        print("Couldn't bind server. Error: %s\n " % msg)

start_listening_touch_events()

def receiver():
    global _close_signal,_connected,_try_reconnect,data,_addr
    print("Socket bind completed")
    while True:
        if _close_signal:
            break
        if _connected:
            # Receiving from client
            recvdata = None
            data = None
            try:
                recvdata, addr = s.recvfrom(9)
                if addr:
                    _addr = addr
            except socket.error,e:
                pass
            if recvdata:
                if not recvdata == "Start\n":
                    parsed = recvdata.split(",")
                    if len(parsed[0])>0 and len(parsed[1]):
                        servo_x = int(parsed[0])
                        servo_y = int(parsed[1])
                        if servo_x > 600 and servo_x <2400 and servo_y>600 and servo_y<2400:
                            servo_controller.set_duty_cycle_bbt((servo_x,servo_y))
        time.sleep(0.001)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind((_host_ip, _host_port))
_receiver_thread = Thread(target=receiver)
_receiver_thread.start()


def sender(conn):
    global _connected, _try_reconnect, data, _close_signal, ctrllrclass,send_position,message_update
    global message_in_queue,send_position,_addr
    while True:
        if _close_signal:
            break
        if _connected:
            # Receiving from client
            if _connected and send_position:
                ball_position_raw = get_ball_position_in_raw()
                data_x_servo = "{:4d}".format(ball_position_raw[0])
                data_y_servo = "{:4d}".format(ball_position_raw[1])
                data = data_x_servo + "," + data_y_servo + "\n"

                try:
                    if _addr and data:
                        conn.sendto(data,_addr)
                except socket.error ,e :
                    pass
            elif not _connected and _try_reconnect:
                print("Connection is not online, will try to connect again")
                break
            elif not _connected and not _try_reconnect:
                print("Connection is not online, closing application")
                break

        time.sleep(0.004)

start_new_thread(sender, (s,))

try:
    while True:
        if _close_signal:
            break
        time.sleep(0.5)
except KeyboardInterrupt:
    _close_signal = True
    _keep_listening_touch_events = False
    pass


print("Close interrupt received.")
#_close_signal = True
if not _connected:
    print("No connection, closing socket")
    s1 = socket.socket(socket.AF_INET,
                  socket.SOCK_DGRAM).connect((_host_ip, _host_port))
    # s1.close()
print("Closing TCP Server")
time.sleep(1)
print("Closing controller object")
servo_controller.close()
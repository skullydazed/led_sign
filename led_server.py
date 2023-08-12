#!/usr/bin/env python
"""Server to control the LED sign.
"""
from os import environ
from socket import gethostname
from threading import Thread
from time import sleep
from queue import Queue

from serial import Serial
from gourd import Gourd

MQTT_USER = environ.get('MQTT_USER', '')
MQTT_PASS = environ.get('MQTT_PASSWD', '')
MQTT_HOST = environ.get('MQTT_HOST', '172.16.22.1')
MQTT_PORT = int(environ.get('MQTT_PORT', '1883'))
MQTT_QOS = int(environ.get('MQTT_QOS', 1))
MQTT_TIMEOUT = int(environ.get('MQTT_TIMEOUT', '30'))
MQTT_BASE_TOPIC = environ.get('MQTT_BASE_TOPIC', 'ledsign')
MQTT_LOCAL_HOST = environ.get('MQTT_LOCAL_HOST', gethostname())
MQTT_SIGN_NUM = environ.get('MQTT_SIGN_NUM', '1')
SERIAL_DEVICE = environ.get('SERIAL_DEVICE', '/dev/ttyACM1')

app = Gourd(app_name=MQTT_BASE_TOPIC, mqtt_host=MQTT_HOST, mqtt_port=MQTT_PORT, username=MQTT_USER, password=MQTT_PASS, timeout=MQTT_TIMEOUT)
start_char = b'<'
end_char = b'\n'
mqtt_topic = f'{MQTT_BASE_TOPIC}/{MQTT_LOCAL_HOST}/{MQTT_SIGN_NUM}'
mqtt_queue = Queue(0)

response_codes = {
    '001': 'version',
    # Logs
    '010': 'log_notset',
    '011': 'log_debug',
    '012': 'log_info',
    '013': 'log_warn',
    '014': 'log_error',
    '015': 'log_critical',
    # Settings
    '020': 'justification',
    '021': 'effect_in',
    '022': 'effect_out',
    '023': 'animation_speed',
    '024': 'pause_time',
    '025': 'num_columns',
    '026': 'intensity',
    '027': 'invert',
    # Display
    '030': 'message',
}

commands = {
    # Control
    'reinit': b'001',
    # Settings
    'justification': b'020',
    'effect_in': b'021',
    'effect_out': b'022',
    'animation_speed': b'023',
    'pause_time': b'024',
    'intensity': b'026',
    'invert': b'027',
    # Display
    'message': b'030',
}

justifications = {
    'left': 0,
    'center': 1,
    'right': 2,
}
int_justifications = {v:k for k,v in justifications.items()}

text_effects = {
    'no_effect': 0,           # Used as a place filler, executes no operation
    'print': 1,               # Text just appears (printed)
    'scroll_up': 2,           # Text scrolls up through the display
    'scroll_down': 3,         # Text scrolls down through the display
    'scroll_left': 4,         # Text scrolls right to left on the display
    'scroll_right': 5,        # Text scrolls left to right on the display
    'sprite': 6,              # Text enters and exits using user defined sprite
    'slice': 7,               # Text enters and exits a slice (column) at a time from the right
    'mesh': 8,                # Text enters and exits in columns moving in alternate direction (U/D)
    'fade': 9,                # Text enters and exits by fading from/to 0 and intensity setting
    'dissolve': 10,           # Text dissolves from one display to another
    'blinds': 11,             # Text is replaced behind vertical blinds
    'random': 12,             # Text enters and exits as random dots
    'wipe': 13,               # Text appears/disappears one column at a time, looks like it is wiped on and off
    'wipe_cursor': 14,        # WIPE with a light bar ahead of the change
    'scan_horiz': 15,         # Scan the LED column one at a time then appears/disappear at end
    'scan_horizx': 16,        # Scan a blank column through the text one column at a time then appears/disappear at end
    'scan_vert': 17,          # Scan the LED row one at a time then appears/disappear at end
    'scan_vertx': 18,         # Scan a blank row through the text one row at a time then appears/disappear at end
    'opening': 19,            # Appear and disappear from the center of the display, towards the ends
    'opening_cursor': 20,     # OPENING with light bars ahead of the change
    'closing': 21,            # Appear and disappear from the ends of the display, towards the middle
    'closing_cursor': 22,     # CLOSING with light bars ahead of the change
    'scroll_up_left': 23,     # Text moves in/out in a diagonal path up and left (North East)
    'scroll_up_right': 24,    # Text moves in/out in a diagonal path up and right (North West)
    'scroll_down_left': 25,   # Text moves in/out in a diagonal path down and left (South East)
    'scroll_down_right': 26,  # Text moves in/out in a diagonal path down and right (North West)
    'grow_up': 27,            # Text grows from the bottom up and shrinks from the top down
    'grow_down': 28,          # Text grows from the top down and and shrinks from the bottom up
}
int_text_effects = {v:k for k,v in text_effects.items()}


def send_to_mqtt(command, args):
    app.log.debug('send_to_mqtt("%s", "%s")', command, args)
    if command == 'justification':
        args = int_justifications[int(args)]
    elif command in ['effect_in', 'effect_out']:
        args = int_text_effects[int(args)]
    app.publish(f'{mqtt_topic}/{command}', args)


def led_sign_thread():
    """Thread that handles communication with the sign over usb-serial.
    """
    sign = Serial(SERIAL_DEVICE)
    sign.flushInput()

    def send_command(command, argument=None):
        """Send a command to the sign.
        """
        app.log.info('Sending (%s %s) to Sign over serial.', command, argument)
        cmd = commands[command]
        cmd_string =  [start_char, cmd]

        if argument:
            cmd_string.append(b' ')
            cmd_string.append(argument.encode('ascii'))
        cmd_string.append(end_char)
        cmd_string = b''.join(cmd_string)

        app.log.debug('Sending "%s" to serial.', cmd_string)
        sign.write(cmd_string)
        sign.flush()

    send_command('reinit')
    while True:
        if sign.in_waiting > 0:
            # Handle output from the sign
            app.log.debug("Reading output from the serial device.")
            line = sign.read_until(end_char)[:-1]  # Get everything except the end_char
            line = line.split(start_char, 1)[-1]  # Remove any junk data from the buffer
            cmd, args = line.decode().split(' ', 1)

            if cmd in response_codes:
                send_to_mqtt(response_codes[cmd], args)
            else:
                app.log.error('Unknown response code: %s (Args: %s)', cmd, args)

        # Handle commands from mqtt
        while not mqtt_queue.empty():
            new_cmd, args = mqtt_queue.get()
            send_command(new_cmd, args)
            mqtt_queue.task_done()

        sleep(.01)


@app.subscribe(f'{mqtt_topic}/#')
def process_mqtt(message):
    command = message.topic[len(mqtt_topic)+1:]

    if command.endswith('/set'):
        command = command[:-4]

        if command in commands:
            if command == 'justification':
                args = str(justifications[message.payload])
            elif command in ['effect_in', 'effect_out']:
                args = str(text_effects[message.payload])
            else:
                args = message.payload

            mqtt_queue.put((command, args))
        else:
            app.log.error('Unknown command: %s', command)


# Start the processing of threads
serial_thread = Thread(target=led_sign_thread)
serial_thread.start()

# Arduino LED Sign with MQTT frontend

This is a project to control an 8 by 8 (or larger) matrix of LEDs driven by a MAX7219 and an Arduino. It connects to a host computer over USB serial, exposing control of the LED sign over MQTT.

## Required Hardware

* Any Arduino, I developed using a Teensy++ 2.0
* LED Matrix, you can find many on Amazon by searching 8x8 led matrix max7219
* Any computer. You can use your desktop/laptop or a Raspberry Pi

### Building your sign

This is out of scope for this README. A good tutorial to follow is here: https://lastminuteengineers.com/max7219-dot-matrix-arduino-tutorial/

## Required Software

* [Arduino IDE](https://www.arduino.cc/en/software)
* [Python 3.7+](https://python.org)
* [Gourd](https://github.com/clueboard/gourd)
* [PySerial](https://pyserial.readthedocs.io/en/latest/index.html)
* [Paho MQTT](https://eclipse.dev/paho/index.php?page=clients/python/index.php)

To install Gourd, PySerial, and Paho MQTT you can run:

    python3 -m pip install pyserial paho-mqtt

## Setup

### Arduino

Edit the `LED_Sign.ino` file and change the following defines:

* `HARDWARE_TYPE`: This should match the matrix you've purchased
* `MAX_DEVICES`: This is the number of 8x8 matrices you have connected
* `CS_PIN`: This is the activate pin for SPI, sometimes called SS

Flash this to your Arduino. Open the serial monitor, select "New Line" as your line ending, and type in `<001`. You should get a response like this:

    <020 0
    <021 1
    <022 0
    <023 500
    <024 1000
    <026 7
    <027 0
    <001 LED Sign v1.0.0
    <030 Hi

Your sign should also be displaying "Hi" now.

**Important**: You must close the serial monitor now or the next step will fail.

### Python

Edit the `led_server.py` file and set `SERIAL_DEVICE` to the serial port for your Arduino. There are other settings you can change as well, or you can set them at runtime by setting shell environment variables.

Run the server like this:

    gourd led_server:app

## MQTT Interface

By default it will send messages to topics under this root:

    ledsign/{your_hostname}/1

The current settings for the following will be sent as individual topics:

* `justification`: How the text aligns, `left`, `center`, or `right`
* `effect_in`: The animation to use when text enters the sign. 
* `effect_out`: The animation to use when text leaves the sign
    * For both `effect_in` and `effect_out` see [MD Parola](https://majicdesigns.github.io/MD_Parola/_m_d___parola_8h.html#acf3b849a996dbbe48ca173d2b0b82eda) for a complete list of animation. We have removed the `PA_` prefix and lower-cased the names.
* `animation_speed`: How long (in ms) to pause between animation frames. Lower is faster.
* `pause_time`: How long (in ms) to pause once the animation is complete.
* `intensity`: How bright the LEDs are, 0-15
* `invert`: Whether the display should be inverted, 0-1
* `message`: The message currently being displayed on the sign
* `version`: The version of the LED firmware. This variable is read-only.

You can set the value of any of these by appending `/set` to the topic name, and publish to that. For example, this is the topic I write to when I set the message for my LED sign:

    ledsign/zayante/1/message/set

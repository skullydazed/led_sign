#include <errno.h>
#include <stdio.h>
#include <MD_Parola.h>
#include <MD_MAX72xx.h>
#include <SPI.h>

#define HARDWARE_TYPE MD_MAX72XX::PAROLA_HW
#define MAX_DEVICES 1
#define NUM_COLS 8    // FIXME: This should me MAX_DEVICES*8
#define CS_PIN    20  // or SS
#define DEFAULT_JUSTIFICATION PA_LEFT
#define DEFAULT_EFFECT_IN PA_PRINT
#define DEFAULT_EFFECT_OUT PA_NO_EFFECT
#define DEFAULT_SPEED 500
#define DEFAULT_PAUSE 1000
#define DEFAULT_INTENSITY 7
#define DEFAULT_INVERT false

const byte numChars = 64;
const char startChar = '<';
const char endChar = '\n';
boolean newData = false;
boolean recvInProgress = false;
char message_buf[numChars];
char receivedCommand[4];
char receivedChars[numChars];
textEffect_t effectIn = DEFAULT_EFFECT_IN;
textEffect_t effectOut = DEFAULT_EFFECT_OUT;
textPosition_t messageJustification = DEFAULT_JUSTIFICATION;
MD_Parola sign = MD_Parola(HARDWARE_TYPE, CS_PIN, MAX_DEVICES);


void setup(void) {
    receivedCommand[3] = '\0';
    Serial.setTimeout(1000);
    Serial.begin(9600);
    sign.begin();
    delay(1000);  // Give the server side time to initialize/connect
}


void sign_init(void) {
    messageJustification = DEFAULT_JUSTIFICATION;
    effectIn = DEFAULT_EFFECT_IN;
    effectOut = DEFAULT_EFFECT_OUT;
    sign.setSpeed(DEFAULT_SPEED);
    sign.setPause(DEFAULT_PAUSE);
    sign.setIntensity(DEFAULT_INTENSITY);
    sign.setInvert(DEFAULT_INVERT);

    sprintf(message_buf, "%d", messageJustification);
    sendSerial("020", message_buf);
    sprintf(message_buf, "%d", effectIn);
    sendSerial("021", message_buf);
    sprintf(message_buf, "%d", effectOut);
    sendSerial("022", message_buf);
    sprintf(message_buf, "%d", sign.getSpeed());
    sendSerial("023", message_buf);
    sprintf(message_buf, "%d", sign.getPause());
    sendSerial("024", message_buf);
    //sendSerial("025", NUM_COLS);
    sprintf(message_buf, "%d", sign.getIntensity());
    sendSerial("026", message_buf);
    sprintf(message_buf, "%d", sign.getInvert());
    sendSerial("027", message_buf);
    sendSerial("001", "LED Sign v1.0.0");

    signWrite("Hi");
}


void loop(void) {
    recvWithStartEndMarkers();
    if (newData) processMessage(receivedCommand, receivedChars);
    sign.displayAnimate();
}


void processMessage(const char code[3], const char message[numChars]) {
    if (strcmp(code, "030") == 0) {
        signWrite(message);
    } else if (strcmp(code, "001") == 0) {
        sign_init();
    } else if (strcmp(code, "020") == 0) {
        errno = 0;
        static textPosition_t justification = (textPosition_t)strtol(message, (char **)NULL, 10);

        if (errno == 0) {
            messageJustification = justification;
            sendSerial("020", message);
        } else {
            sendSerial("015", "Could not convert 020 payload to int!");
        }
    } else if (strcmp(code, "021") == 0) {
        errno = 0;
        static textEffect_t effect = (textEffect_t)strtol(message, (char **)NULL, 10);

        if (errno == 0) {
            effectIn = effect;
            sendSerial("021", message);
        } else {
            sendSerial("015", "Could not convert 021 payload to int!");
        }
    } else if (strcmp(code, "022") == 0) {
        errno = 0;
        static textEffect_t effect = (textEffect_t)strtol(message, (char **)NULL, 10);

        if (errno == 0) {
            effectOut = effect;
            sendSerial("022", message);
        } else {
            sendSerial("015", "Could not convert 022 payload to int!");
        }
    } else if (strcmp(code, "023") == 0) {
        errno = 0;
        static byte time = (int)strtol(message, (char **)NULL, 10);

        if (errno == 0) {
            sign.setSpeed(time);
            sendSerial("023", message);
        } else {
            sendSerial("015", "Could not convert 023 payload to int!");
        }
    } else if (strcmp(code, "024") == 0) {
        errno = 0;
        static byte time = (int)strtol(message, (char **)NULL, 10);

        if (errno == 0) {
            sign.setPause(time);
            sendSerial("024", message);
        } else {
            sendSerial("015", "Could not convert 024 payload to int!");
        }
    } else if (strcmp(code, "026") == 0) {
        errno = 0;
        static byte intensity = (int)strtol(message, (char **)NULL, 10);

        if (errno == 0) {
            sign.setIntensity(intensity);
            sendSerial("026", message);
        } else {
            sendSerial("015", "Could not convert 026 payload to int!");
        }
    } else if (strcmp(code, "027") == 0) {
        errno = 0;
        static byte inverted = (int)strtol(message, (char **)NULL, 10);

        if (errno == 0) {
            sign.setInvert(inverted);
            sendSerial("027", message);
        } else {
            sendSerial("015", "Could not convert 027 payload to int!");
        }
    } else {
        sendSerial("016", "Unknown Command");
    }
    newData = false;
}


void signWrite(const char message[numChars]) {
    sign.displayText(message, messageJustification, sign.getSpeed(), sign.getPause(), effectIn, effectOut);
    sendSerial("030", message);
}


void sendSerial(const char code[3], const char message[numChars]) {
    Serial.write(startChar);
    Serial.write(code);
    Serial.write(" ");
    Serial.write(message);
    Serial.write(endChar);
}


void recvWithStartEndMarkers() {
    static byte ndx = 0;
    static byte command = 0;
    char rc;
    //char rc_a[2];
    //rc_a[1] = '\0';

    if (Serial.available()) {
        while (newData == false) {
            rc = Serial.read();
            //rc_a[0] = rc;

            if (recvInProgress == true) {
                if (rc == endChar) {
                    receivedChars[ndx] = '\0';  // terminate the string
                    recvInProgress = false;
                    command = 0;
                    ndx = 0;
                    newData = true;
                } else {
                    if (command < 3) {
                        receivedCommand[command] = rc;
                        command++;
                    } else if (command == 3) {
                        command++;  // Ignore the space after the command
                    } else {
                        receivedChars[ndx] = rc;
                        ndx++;
                        if (ndx >= numChars) {
                            ndx = numChars - 1;
                        }
                    }
                }
            } else if (rc == startChar) {
                recvInProgress = true;
            }
        }
    }
}
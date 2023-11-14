from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS, cross_origin
import RPi.GPIO as GPIO
from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
import threading
import cv2
import pygame
import time

in1 = 15
in2 = 14
ena = 18
servo_pin = 23

back_led = 24

GPIO.setmode(GPIO.BCM)

#led 1
GPIO.setmode(GPIO.BCM)
GPIO.setup(back_led, GPIO.OUT)

# servo 
factory = PiGPIOFactory()
servo = AngularServo(servo_pin, min_pulse_width=0.0006, max_pulse_width=0.0023, pin_factory=factory)

# motor 1
GPIO.setup(in1,GPIO.OUT)
GPIO.setup(in2,GPIO.OUT)
GPIO.setup(ena,GPIO.OUT)
GPIO.output(in1,GPIO.LOW)
GPIO.output(in2,GPIO.LOW)

p1=GPIO.PWM(ena,1000)
p1.start(25)

pygame.init()

horn_sound = pygame.mixer.music.load('/home/pi/rc_server/static/horn.wav')

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
socketio = SocketIO(app, cors_allowed_origins="*")

def generate_frames():
    capture = cv2.VideoCapture(0)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 4)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 160)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 120)
    capture.set(cv2.CAP_PROP_FPS, 30)

    while True:
        success, frame = capture.read()
        if not success:
            break
        else:
            # Encode the frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



def main():
    servo.angle = 0
    app.run(host='0.0.0.0', port=5001)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

dirr = 0

@socketio.on('message')
def handle_message(message):
    global dirr

    if message[-1] == 1:
        if pygame.mixer.music.get_busy() == 0:
            pygame.mixer.music.play(horn_sound)
    else:
        pygame.mixer.music.stop()

    if int(message[2]) != 0:
        dirr = 0
        GPIO.output(in2, GPIO.HIGH)
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(back_led, GPIO.LOW)
    elif int(message[1]) != 0:
        dirr = 1
        GPIO.output(in2, GPIO.LOW)
        GPIO.output(in1, GPIO.HIGH)
        GPIO.output(back_led, GPIO.HIGH)
    else:
        GPIO.output(back_led, GPIO.LOW)
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(in2, GPIO.LOW)


    servo.angle = message[0]

    if dirr == 0:
        p1.ChangeDutyCycle(int(message[2]))
    elif dirr == 1:
        p1.ChangeDutyCycle(int(message[1]))


@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


if __name__ == '__main__':
    threading.Thread(target=main).start()
    socketio.run(app, host='0.0.0.0', port=5002)


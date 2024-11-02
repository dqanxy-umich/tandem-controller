from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
import time
import threading
import atexit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
keyboard = KeyboardController()
mouse = MouseController()

inputs = ['MouseX', 'MouseY', 'W', 'A', 'S', 'D', 'Left Click', 'Right Click']
alloc = [5,1,1,1]
user_timeouts = [time.time() for i in alloc]

currentInputs = {
    'MouseX': 0,
    'MouseY': 0,
}
currentMouseInputs = {
    'MouseX': 0.0,
    'MouseY': 0.0,
}
data_lock = threading.Lock()
your_timer = threading.Timer(0, lambda x: None, ())

def interrupt():
    global your_timer
    your_timer.cancel()

def apply_current_inputs_thread():
    global currentInputs
    global currentMouseInputs
    global your_timer
    with data_lock:
        if currentInputs['MouseX'] != 0 or currentInputs['MouseY'] != 0:
            currentMouseInputs['MouseX'] += 20 * currentInputs['MouseX']
            currentMouseInputs['MouseY'] += 20 * currentInputs['MouseY']
            mouse.move(round(currentMouseInputs['MouseX']), round(currentMouseInputs['MouseY']))
            currentMouseInputs['MouseX'] -= round(currentMouseInputs['MouseX'])
            currentMouseInputs['MouseY'] -= round(currentMouseInputs['MouseY'])
            time.sleep(.01)
    your_timer = threading.Timer(.01, apply_current_inputs_thread, ())
    your_timer.start()

def do_stuff_start():
    global your_timer
    your_timer = threading.Timer(.01, apply_current_inputs_thread, ())
    your_timer.start()

@socketio.on('input')
def handle_input(data):
    key = inputs[data.get('user_id')]
    #user_timeouts[data.get('user_id')] = time.time()

    if key in ['W', 'A', 'S', 'D']:
        keyboard.press(key.lower())
        time.sleep(.1)
        emit('response', {'status': 'success', 'key': key})
    elif key in ['Left Click', 'Right Click']:
        if key == 'Left Click':
            mouse.click(Button.left, 1)
        elif key == 'Right Click':
            mouse.click(Button.right, 1)
    if key in ['MouseX', 'MouseY']:
        global currentInputs
        with data_lock:
            currentInputs[key] = data.get('value')
        emit('response', {'status': 'success', 'key': key})

@socketio.on('release')
def handle_release(data):
    key = inputs[data.get('user_id')]
    #user_timeouts[data.get('user_id')] = time.time()

    if key in ['W', 'A', 'S', 'D']:
        keyboard.release(key.lower())
        emit('response', {'status': 'success', 'key': key})
    elif key in ['Left Click', 'Right Click']:
        if key == 'Left Click':
            mouse.click(Button.left, 1)
        elif key == 'Right Click':
            mouse.click(Button.right, 1)
        emit('response', {'status': 'success', 'key': key})
    elif key in ['MouseX', 'MouseY']:
        global currentInputs
        with data_lock:
            currentInputs[key] = 0
        emit('response', {'status': 'success', 'key': key})


@socketio.on('heartbeat')
def handle_heartbeat(data):
    user_id = data.get('timeout')
    user_timeouts[user_id] = time.time()
    emit('response', {'status': 'success', 'user_id': user_id})

@socketio.on('join')
def handle_join(data):
    for i in range(len(user_timeouts)):
        if time.time() - user_timeouts[i] > 10:
            user_timeouts[i] = time.time()
            ind = 0
            for j in range(i):
                ind += alloc[j]
            ids = [ind+x for x in range(alloc[i])]
            emit('joinSuccess', {'status': 'success', 'timeout': i, 'user_id': ids, 'tooltip': "YOU ARE: " + str([inputs[x] for x in ids]), 'isSlider': [inputs[x] in ['MouseX', 'MouseY'] for x in ids]})
            return
    emit('connect_error', {'status': 'error', 'message': 'No available slots'})

@socketio.on('gameplay')
def handle_gameplay(data):
    #user_timeouts[data.get('user_id')] = time.time()
    if data.get('action') == 'input':
        handle_input(data)
    elif data.get('action') == 'release':
        handle_release(data)
    elif data.get('action') == 'heartbeat':
        handle_heartbeat(data)
    emit('response', {'status': 'success', 'key': 'gameplay'})

do_stuff_start()
atexit.register(interrupt)

if __name__ == '__main__':
    socketio.run(app, debug=True)

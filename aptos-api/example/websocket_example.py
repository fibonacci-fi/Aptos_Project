import websocket
import json
import time

def on_message(ws, message):
    print(f"Received message: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    print("Connection opened")
    # Subscribe to overall stats
    ws.send(json.dumps({'event': 'subscribe_overall_stats'}))
    # Subscribe to a specific pool (replace 'pool_address' with an actual address)
    ws.send(json.dumps({'event': 'subscribe_pool', 'data': {'pool_address': 'pool_address'}}))

if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("ws://127.0.0.1:8080/socket.io/?EIO=4&transport=websocket",
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close,
                                header=["Origin: http://127.0.0.1"])
    ws.run_forever()
import machine
import time
import esp32
import esp
import network
import socket
import json
import urequests as requests

# sw = machine.Pin(0, machine.Pin.IN)
led = machine.Pin(2, machine.Pin.OUT)

wlan = network.WLAN(network.STA_IF)

def connect(ssid: str, key: str, timeout=10):
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi network:", ssid)
        try:
            wlan.connect(ssid, key)
            start_time = time.time()
            while not wlan.isconnected():
                if time.time() - start_time > timeout:
                    raise Exception("Connection timeout")
                time.sleep(0.1)
            print(wlan.ifconfig())
            led.on()
            time.sleep(2.5)
            led.off()
            return True
        except Exception as e:
            print("Unable to connect:", str(e))
            return False
    else:
        print("Already connected, disconnect from current and connect new network")
        return True

# connect("Lawrence", "DontBeGay1125")

def start_server():
    if wlan.isconnected():
        ip_address = wlan.ifconfig()[0]
        print("ESP32 IP address:", ip_address)

        # Sending the IP address to GoLang server
        send_ip_to_server(ip_address)

        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        s = socket.socket()
        s.bind(addr)
        s.listen(1)

        print("listening on address: ", addr)
        while True:
            cl, cl_addr = s.accept()
            print("new client connected from: ", cl_addr)
            request = cl.recv(1024)

            headers = request.decode().split('\r\n\r\n')[0]
            method = headers.split('\r\n')[0].split(' ')[0]
            
            if method == "POST":
                get_notification_signal(cl, request)

            elif method == "GET":
                render_homepage(cl)
                
            else:
                response = "Method not supported!"
                cl.send('HTTP/1.0 400 OK\r\nContent-type: text/html\r\n\r\n'.encode())
                cl.send(response.encode())
    else:
        print("WiFi must be connected before server could start")
        
def disconnect():
    print("disconnecting from wifi...")
    if wlan.isconnected():
        wlan.disconnect()
        print("wifi disconnected successfully")
    else:
        print("no connected wifi")


def get_notification_signal(cl, request):
    
    expected_keys = {
        'content': str,
        'type': str,
        'time': str,
        'trip_id': str
    }

    try:
        body = request.decode().split('\r\n\r\n')[1]
        received_request = json.loads(body)

        is_valid = all(
            key in received_request and isinstance(received_request[key], expected_type)
            for key, expected_type in expected_keys.items()
        )

        if is_valid:
            msg = {
                "status": "success"
            }
            response = json.dumps(msg)

            cl.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n'.encode())
            cl.send(response.encode("UTF-8"))
            cl.close()

            req_type = received_request["type"]
            if req_type == "TripRequest":
                counter = 0
                while counter < 15:
                    led.on()
                    time.sleep(0.1)
                    led.off()
                    time.sleep(0.1)
                    counter += 1
            else:
                pass
        
        else:
            msg = {
                "status": "warning",
                "message": "Request structure is invalid"
            }

            response = json.dumps(msg)
            cl.send('HTTP/1.0 400 OK\r\nContent-type: application/json\r\n\r\n'.encode())
            cl.send(response.encode("UTF-8"))
            cl.close()

        
    except json.JSONDecodeError:
        print("Invalid json received")
        cl.send('HTTP/1.0 400 Bad Request\r\nContent-type: application/json\r\n\r\n'.encode())
        cl.send(json.dumps({"status": "error", "message": "Invalid json"}).encode("UTF-8"))
        cl.close()

def render_homepage(cl):

    html_template = """
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>My ESP32 Project</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        max-width: 600px;
                        margin: 20px auto;
                        padding: 0 20px;
                    }}
                    h1 {{
                        color: #333;
                    }}
                    p {{
                        line-height: 1.6;
                    }}
                </style>
            </head>
            <body>
                <h1>Welcome to My ESP32 Project</h1>
                <p>This project aims to BLAH BLAH BLAH. It utilizes the ESP32 microcontroller to do something BLAH BLAH BLAH.</p>
                <p>More details or updates are coming</p>
                <p>Current IP Address: {ip_address}</p>
            </body>
        </html>
    """
    
    ip_address = wlan.ifconfig()[0]
    formatted_html = html_template.format(ip_address=ip_address)

    cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'.encode())
    cl.send(formatted_html.encode())
    cl.close()

def send_ip_to_server(ip: str):
    mac = wlan.config("mac")
    mac_addr = ':'.join('{:02x}'.format(b) for b in mac)
    ip_addr = wlan.ifconfig()[0]
    data =  {
        "mac_addr": mac_addr,
        "ip_addr":  ip_addr
    }

    print("Data to send: ",data)

    # Golang server domain or cloud whatever
    url = "http://192.168.8.102:2323/ip"

    try:
        response = requests.put(url, json=data)
        
        print('Response status code:', response.status_code)
        print('Response content:', response.text)
        
        response.close()

    except Exception as e:
        print('Error making POST request:', e)




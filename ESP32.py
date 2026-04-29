from machine import Pin, ADC, PWM
import time
import network
import urequests
import gc
import dht

# --- CONFIGURARE REȚEA ---
WIFI_SSID = "A"  
WIFI_PASS = "123456710"            
IP_SERVER = "10.94.135.224"              

# --- ROLURILE FIZICE ALE PLĂCUȚEI ---
CAMERA_SENZOR = "E"   
USA_START = "C"
USA_DESTINATIE = "E"

URL_UPDATE = f"http://{IP_SERVER}:5000/update_camera"
URL_STATUS = f"http://{IP_SERVER}:5000/stare_usa/{USA_START}/{USA_DESTINATIE}"

# --- HARDWARE ---
led_rosu = PWM(Pin(3), freq=1000)
led_verde = PWM(Pin(2), freq=1000)
senzor_mq = ADC(Pin(4))
senzor_mq.atten(ADC.ATTN_11DB)
senzor_dht = dht.DHT22(Pin(10)) 

def set_leds(r, v):
    led_rosu.duty_u16(65535 if r else 0)
    led_verde.duty_u16(65535 if v else 0)

# --- CONEXIUNE WI-FI ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)
print("Conectare la server", end="")
while not wlan.isconnected():
    print(".", end="")
    time.sleep(0.5)
print("\nConexiune stabilită! IP Local:", wlan.ifconfig()[0])

set_leds(False, True)

# --- BUCLA PRINCIPALĂ ---
while True:
    try:
        # 1. CITIRE SENZORI
        gaz = senzor_mq.read()
        temperatura = 22.0 # Valori de siguranță implicite
        umiditate = 50.0
        
        try:
            senzor_dht.measure()
            temperatura = senzor_dht.temperature()
            umiditate = senzor_dht.humidity()
        except OSError:
            print("Avertisment: Citire DHT22 eșuată.")

        # 2. TRIMITERE DATE RAW CĂTRE SERVER
        payload = {
            "camera": CAMERA_SENZOR, 
            "gaz": gaz, 
            "temp": temperatura, 
            "umiditate": umiditate
        }
        
        res_update = urequests.post(URL_UPDATE, json=payload, headers={'Connection': 'close'})
        res_update.close()

        # 3. INTEROGARE CULOARE UȘĂ
        res_status = urequests.get(URL_STATUS, headers={'Connection': 'close'})
        date_usa = res_status.json()
        res_status.close()
        
        # 4. EXECUTARE COMANDĂ SERVER (LED-URI)
        if date_usa['comanda'] == "ROSU":
            set_leds(True, False)
        else:
            set_leds(False, True)
            
        print(f"[Trimis -> G:{gaz} T:{temperatura}°C] [Primit -> {date_usa['comanda']}: {date_usa['motiv']}]")

    except Exception as e:
        print("Eroare de comunicare HTTP:", e)
        
    finally:
        gc.collect() 
        
    time.sleep(2) # Ritm de actualizare la 2 secunde

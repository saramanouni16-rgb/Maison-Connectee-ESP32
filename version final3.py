from machine import Pin, ADC, I2C, PWM
from time import sleep
import network
import urequests
import json
from i2c_lcd import I2cLcd  # Assure-toi que le module i2c_lcd.py est présent

# ---------------------- CAPTEUR GAZ ----------------------
gaz = ADC(Pin(34))
gaz.atten(ADC.ATTN_11DB)
gaz.width(ADC.WIDTH_12BIT)

# ---------------------- CAPTEUR PLUIE ----------------------
pluie = Pin(25, Pin.IN)

# ---------------------- LED + BUZZER ----------------------
led = Pin(19, Pin.OUT)
buzzer = PWM(Pin(18))
SEUIL_GAZ = 2000

# ---------------------- LCD ----------------------
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
lcd = I2cLcd(i2c, 0x27, 2, 16)  # Adresse 0x27, 2 lignes, 16 colonnes

# ---------------------- WIFI + FIREBASE ----------------------
SSID = "UH2CGUEST"
PASSWORD = "uh2c@2021"
FIREBASE_URL = "https://embrs-8f3fa-default-rtdb.firebaseio.com/"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Connexion WiFi...")
    while not wlan.isconnected():
        print(".", end="")
        sleep(0.5)
    print("\nWiFi CONNECTE :", wlan.ifconfig())

def send_to_firebase(path, value):
    url = FIREBASE_URL + path + ".json"
    data = json.dumps(value)
    try:
        r = urequests.put(url, data=data)
        print("Firebase:", r.text)
        r.close()
    except Exception as e:
        print("Erreur Firebase:", e)

# ---------------------- FONCTION ALERTE DANGER ----------------------
def send_danger_alert(gaz_valeur, pluie_etat):
    message = {
        "message": "Attention ! Danger detecte !",
        "niveau_gaz": gaz_valeur,
        "etat_meteo": "pluie" if pluie_etat == 1 else "sec",
        "conseil": "Prenez toutes les precautions !"
    }
    send_to_firebase("alerte_danger", message)

# ---------------------- FONCTIONS DE MISE A JOUR ----------------------
def update_pluie_brut(val):
    send_to_firebase("pluie/brut", val)

def update_pluie_etat(txt):
    send_to_firebase("pluie/etat", txt)

def update_system_state(val):
    send_to_firebase("systeme/etat", val)

# ---------------------- PROGRAMME PRINCIPAL ----------------------
connect_wifi()
update_system_state(1)   # système = ON
led_state = 0

while True:
    # Lecture gaz
    valeur = gaz.read()
    voltage = round(valeur * 3.3 / 4095, 2)

    # Lecture pluie
    pluie_val = pluie.value()
    pluie_text = "pluie" if pluie_val == 1 else "sec"

    # Envoi données pluie
    update_pluie_brut(pluie_val)
    update_pluie_etat(pluie_text)

    # Bargraph
    bar_len = int((valeur / 4095) * 10)
    bargraph_display = ("#" * bar_len + " " * 10)[:10]

    # Alerte gaz
    if valeur > SEUIL_GAZ:
        led_state = not led_state
        led.value(led_state)
        buzzer.freq(1000)
        buzzer.duty(512 if led_state else 0)

        lcd.clear()
        lcd.putstr("!!! ALERTE GAZ !!!")
        lcd.move_to(0, 1)
        lcd.putstr(pluie_text)

        send_to_firebase("gaz/alerte", 1)
        send_to_firebase("gaz/valeur", valeur)

        # Envoi alerte complète
        send_danger_alert(valeur, pluie_val)

    else:
        led.value(0)
        buzzer.duty(0)
        lcd.clear()
        lcd.putstr("Gaz:{} V:{}".format(valeur, voltage))
        lcd.move_to(0, 1)
        lcd.putstr(bargraph_display + " " + pluie_text)

        send_to_firebase("gaz/alerte", 0)
        send_to_firebase("gaz/valeur", valeur)

    # Console
    print("Gaz:", valeur, "| Pluie:", pluie_text)
    sleep(1)

#include <ESP8266WiFi.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP8266HTTPClient.h>

const char* ssid = "WiFi_ADI";
const char* password = "WiFi_SIFRE";
const char* serverUrl = "http://your_server_ip:5000/api/kart-okuma";

#define RST_PIN D3
#define SS_PIN D4

MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("WiFi bağlanıyor...");
  }
}

void loop() {
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial())
    return;

  String kart_no = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    kart_no += String(mfrc522.uid.uidByte[i], HEX);
  }

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    String json = "{"kart_no": "" + kart_no + ""}";
    int httpCode = http.POST(json);
    String payload = http.getString();
    Serial.println(payload);
    http.end();
  }

  delay(3000);
}

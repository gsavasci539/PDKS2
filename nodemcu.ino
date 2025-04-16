#include <Wire.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <SD.h>

// WiFi bilgileri
const char* ssid = "Wokwi-GUEST";  // WiFi SSID
const char* password = "";  // WiFi password

// Flask API URL (Flask backend'inizin IP'sine göre değiştirin)
const String api_url_entry = "http://127.0.0.1:5000/attendance/entry";
const String api_url_exit = "http://127.0.0.1:5000/attendance/exit";
const String api_url_log = "http://127.0.0.1:5000/log";  // API'ye log gönderme URL'si

// RFID okuyucu pinleri
#define RST_PIN 22  // Reset pin (ESP32 için uygun bir pin seçilmiştir)
#define SS_PIN 21  // Slave select pin (ESP32 için uygun bir pin seçilmiştir)

// Röle kontrol pini
#define RELAY_PIN 23  // Röle bağlı olan GPIO pin

// Buzzer pini
#define BUZZER_PIN 18  // Buzzer bağlı olan GPIO pin

// RGB LED Pinleri
#define RED_PIN 18  // Kırmızı LED pini
#define GREEN_PIN 5  // Yeşil LED pini
#define BLUE_PIN 19  // Mavi LED pini

// SD kart pini
#define SD_CS_PIN 4  // SD kartın chip select pini (ESP32 için uygun pin)

MFRC522 mfrc522(SS_PIN, RST_PIN);  // RFID okuyucu nesnesi

// Kart okuma durumu takibi
bool isEntry = true;  // Başlangıçta giriş olarak varsayalım

void setup() {
  Serial.begin(115200);

  // Wi-Fi bağlantısını başlat
  WiFi.begin(ssid, password);

  int wifiAttempts = 0;  // Wi-Fi bağlantı deneme sayacı
  const int maxAttempts = 5;  // Maksimum deneme sayısı
  const int waitTime = 1000;  // 1 saniye bekleme
  const int retryWaitTime = 300000;  // 5 dakika bekleme (300000 ms)

  // RGB LED pinlerini çıkış olarak ayarla
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);

  // Röle ve buzzer pinlerini çıkış olarak ayarla
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  // SPI başlat
  SPI.begin();  // SPI iletişimi başlat
  mfrc522.PCD_Init();  // RFID okuyucuyu başlat

  // Wi-Fi'ye bağlanmayı dene
  while (wifiAttempts < maxAttempts) {
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("Connected to WiFi!");
      sendLogData("Connecting to WiFi...", "info");
      setRGBColor(0, 0, 255);  // Wi-Fi bağlı, mavi yanacak
      break;
    } else {
      Serial.println("Connecting to WiFi...");
           sendLogData("Connecting to WiFi...", "info");

      wifiAttempts++;  // Deneme sayısını artır
      delay(waitTime);  // 1 saniye bekle
    }
  }

  // Eğer Wi-Fi bağlantısı sağlanamadıysa, SD kart yazma işlemine geç
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, switching to SD card operation...");
     sendLogData("WiFi not connected, switching to SD card operation...", "info");
    setRGBColor(255, 0, 0);  // Wi-Fi bağlantısı yok, kırmızı yanacak

    // SD kartı başlat
    if (!SD.begin(SD_CS_PIN)) {
      Serial.println("SD card initialization failed!");
      sendLogData("SD card initialization failed!", "error");
     // SD kart yoksa işlemi durdur
    } else {
      Serial.println("SD card initialized.");
      sendLogData("SD card initialized.", "info");
    }

    // SD kart üzerinde veri yazma işlemi başlat
    while (true) {
      File dataFile = SD.open("attendance_log.txt", FILE_WRITE);
      if (dataFile) {
        dataFile.println("Veri yazılıyor...");
        sendLogData("Veri yazılıyor...", "info");
        dataFile.close();
        Serial.println("Data written to SD card.");
        sendLogData("Data written to SD card.", "info");
      } else {
        Serial.println("Error opening file for writing.");
        sendLogData("Error opening file for writing.", "error");
      }
      delay(2000);  // 2 saniye bekle (SD karta yazma işlemi)

      // 5 dakika sonra Wi-Fi'yi tekrar dene
      Serial.println("Waiting 5 minutes before retrying WiFi connection...");
      sendLogData("Waiting 5 minutes before retrying WiFi connection...", "alert");
      delay(retryWaitTime);  // 5 dakika bekle (300000 ms)
      Serial.println("Retrying WiFi connection...");
      sendLogData("Retrying WiFi connection", "alert");

      // Wi-Fi'ye tekrar bağlanmayı dene
      WiFi.begin(ssid, password);
      wifiAttempts = 0;  // Deneme sayısını sıfırla
    }
  }

  // Eğer Wi-Fi bağlantısı sağlandıysa, burada başka işlemler yapılabilir
}

void loop() {
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String rfid_uid = "";

    // RFID kartın UID'sini al ve employee_id olarak kullan
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      rfid_uid += String(mfrc522.uid.uidByte[i], HEX);
    }

    Serial.print("Card UID (employee_id): ");
    Serial.println(rfid_uid);

    // Giriş veya çıkış işlemi için zaman al
    String current_time = getCurrentTime();  // Zaman bilgisi al

    // Giriş veya çıkış işlemi belirle
    if (isEntry) {
      // Giriş işlemi yapılacak
      if (WiFi.status() == WL_CONNECTED) {
        int entry_response = sendEntryData(rfid_uid, current_time);
        if (entry_response == 200) {
          setRGBColor(0, 255, 0);  // Giriş başarılı, yeşil yanacak
         sendLogData("Entry successful for employee ID: " + rfid_uid, "info"); // Log gönder
        } else {
          setRGBColor(255, 0, 0);  // Giriş başarısız, kırmızı yanacak
          sendLogData("Entry failed for employee ID: " + rfid_uid, "error"); // Log gönder
        }
      } else {
        saveToSDCard("entry", rfid_uid, current_time, "");
      }

      // Röleyi aç (giriş yapıldı) ve buzzeri çal
      digitalWrite(RELAY_PIN, HIGH);  // Röleyi aç (HIGH = açık)
      digitalWrite(BUZZER_PIN, HIGH);  // Buzzer'ı aç (HIGH = çal)
      delay(500);  // Buzzer'ı 0.5 saniye çaldır
      digitalWrite(BUZZER_PIN, LOW);  // Buzzer'ı kapat (LOW = kapalı)

      // Giriş tamamlandığında çıkışa geç
      isEntry = false;
    } else {
      // Çıkış işlemi yapılacak
      if (WiFi.status() == WL_CONNECTED) {
        int exit_response = sendExitData(rfid_uid, current_time);
        if (exit_response == 200) {
          setRGBColor(0, 255, 0);  // Çıkış başarılı, yeşil yanacak
         sendLogData("Exit successful for employee ID: " + rfid_uid, "info"); // Log gönder
        } else {
          setRGBColor(255, 0, 0);  // Çıkış başarısız, kırmızı yanacak
          sendLogData("Exit failed for employee ID: " + rfid_uid,"error"); // Log gönder
        }
      } else {
        saveToSDCard("exit", rfid_uid, "", current_time);
      }

      // Röleyi aç (çıkış yapıldı) ve buzzeri çal
      digitalWrite(RELAY_PIN, HIGH);  // Röleyi aç (HIGH = açık)
      digitalWrite(BUZZER_PIN, HIGH);  // Buzzer'ı aç (HIGH = çal)
      delay(500);  // Buzzer'ı 0.5 saniye çaldır
      digitalWrite(BUZZER_PIN, LOW);  // Buzzer'ı kapat (LOW = kapalı)

      // Çıkış tamamlandığında girişe geç
      isEntry = true;
    }

    delay(2000);  // 2 saniye bekle

    // Wi-Fi bağlantısı varsa, SD karttaki verileri gönder
    if (WiFi.status() == WL_CONNECTED) {
      sendStoredDataFromSDCard();
    }
  }
}

String getCurrentTime() {
  // Güncel zamanı ISO formatında al (örneğin: "2025-04-07T12:30:00")
  String currentTime = "2025-04-07T12:30:00";  // Gerçek zaman bilgisi almak için NTP kullanabilirsiniz
  return currentTime;
}

// Entry verisini API'ye gönder
int sendEntryData(String employee_id, String timestamp) {
  HTTPClient http;
  http.begin(api_url_entry);
  http.addHeader("Content-Type", "application/json");

  String jsonData = "{\"employee_id\": \"" + employee_id + "\", \"timestamp\": \"" + timestamp + "\"}";
  int httpResponseCode = http.POST(jsonData);

  http.end();
  return httpResponseCode;
}

// Exit verisini API'ye gönder
int sendExitData(String employee_id, String timestamp) {
  HTTPClient http;
  http.begin(api_url_exit);
  http.addHeader("Content-Type", "application/json");

  String jsonData = "{\"employee_id\": \"" + employee_id + "\", \"timestamp\": \"" + timestamp + "\"}";
  int httpResponseCode = http.POST(jsonData);

  http.end();
  return httpResponseCode;
}


// Log verisini API'ye gönder (log türü eklenmiş)
void sendLogData(String logMessage, String logType) {
  HTTPClient http;
  http.begin(api_url_log);
  http.addHeader("Content-Type", "application/json");

  // JSON verisi: log mesajı ve log türü
  String jsonData = "{\"log\": \"" + logMessage + "\", \"log_type\": \"" + logType + "\"}";
  http.POST(jsonData);
  http.end();
}


// SD karttaki verileri API'ye gönder (Eğer Wi-Fi bağlantısı yoksa)
void sendStoredDataFromSDCard() {
  File dataFile = SD.open("attendance_log.txt", FILE_READ);
  if (dataFile) {
    while (dataFile.available()) {
      String logEntry = dataFile.readStringUntil('\n');

    }
    dataFile.close();
  }
}

// SD kartta veri kaydet (Wi-Fi yoksa)
void saveToSDCard(String action, String employee_id, String entry_time, String exit_time) {
  File dataFile = SD.open("attendance_log.txt", FILE_WRITE);
  if (dataFile) {
    dataFile.print(action);
    dataFile.print(" | ");
    dataFile.print(employee_id);
    dataFile.print(" | ");
    dataFile.print(entry_time);
    dataFile.print(" | ");
    dataFile.println(exit_time);
    dataFile.close();
  } else {
    Serial.println("Error opening file for writing.");
  }
}

// RGB LED renk ayarlarını yap
void setRGBColor(int red, int green, int blue) {
  analogWrite(RED_PIN, red);
  analogWrite(GREEN_PIN, green);
  analogWrite(BLUE_PIN, blue);
}

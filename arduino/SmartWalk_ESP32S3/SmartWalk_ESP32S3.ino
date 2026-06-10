/*
 * SmartWalk — ESP32-S3 Kamera Yayın Kodu
 * DFRobot ESP32-S3 AI Camera için
 *
 * Bu kod ESP32-S3'ü yerel ağda bir HTTP sunucusuna dönüştürür.
 * Python kodu http://<IP>/capture adresinden JPEG frame çeker.
 *
 * Yükleme:
 *   1. Arduino IDE → Dosya → Tercihler → Ek Board URL:
 *      https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
 *   2. Board Manager → "esp32" kur
 *   3. Board: "ESP32S3 Dev Module" seç
 *   4. WIFI_SSID ve WIFI_PASS'i kendi ağınla değiştir
 *   5. Yükle → Seri Monitör'de IP adresini gör
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// ======== WiFi Ayarları — BUNLARI DEĞİŞTİR ========
const char* WIFI_SSID = "WiFi_Adin";
const char* WIFI_PASS = "WiFi_Sifren";
// ===================================================

// DFRobot ESP32-S3 AI Camera pin konfigürasyonu
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  15
#define SIOD_GPIO_NUM   4
#define SIOC_GPIO_NUM   5
#define Y9_GPIO_NUM    16
#define Y8_GPIO_NUM    17
#define Y7_GPIO_NUM    18
#define Y6_GPIO_NUM    12
#define Y5_GPIO_NUM    10
#define Y4_GPIO_NUM     8
#define Y3_GPIO_NUM     9
#define Y2_GPIO_NUM    11
#define VSYNC_GPIO_NUM  6
#define HREF_GPIO_NUM   7
#define PCLK_GPIO_NUM  13

WebServer server(80);

// ---- /capture endpoint: tek JPEG frame döner ----
void handleCapture() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    server.send(500, "text/plain", "Kamera hatasi");
    return;
  }
  server.sendHeader("Content-Disposition", "inline; filename=capture.jpg");
  server.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

// ---- / endpoint: durum sayfası ----
void handleRoot() {
  String html = "<h2>SmartWalk ESP32-S3 Hazir</h2>";
  html += "<p>Frame almak icin: <a href='/capture'>/capture</a></p>";
  server.send(200, "text/html", html);
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n[SmartWalk] Baslatiliyor...");

  // Kamera konfigürasyonu
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Yüksek çözünürlük: PSRAM varsa VGA, yoksa QVGA
  if (psramFound()) {
    config.frame_size   = FRAMESIZE_VGA;   // 640x480
    config.jpeg_quality = 12;              // 0-63, düşük = iyi kalite
    config.fb_count     = 2;
  } else {
    config.frame_size   = FRAMESIZE_QVGA;  // 320x240
    config.jpeg_quality = 15;
    config.fb_count     = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[HATA] Kamera baslatilamadi: 0x%x\n", err);
    Serial.println("Pin konfigurasyonunu kontrol et.");
    return;
  }
  Serial.println("[OK] Kamera hazir.");

  // WiFi bağlantısı
  Serial.printf("[WiFi] %s agina baglaniliyor", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("[WiFi] Baglandi! IP adresi: ");
  Serial.println(WiFi.localIP());
  Serial.print("[SmartWalk] Python'a gir: CAMERA_URL = \"http://");
  Serial.print(WiFi.localIP());
  Serial.println("/capture\"");

  // HTTP sunucusu
  server.on("/", handleRoot);
  server.on("/capture", handleCapture);
  server.begin();
  Serial.println("[Server] HTTP sunucusu baslatildi.");
}

void loop() {
  server.handleClient();
}

#include "esp_camera.h"
#include <WiFi.h>
#include <U8g2lib.h>
#include "esp_http_server.h"

// --- I2C ve OLED Pin Tanımlamaları ---
#define OLED_SDA 44
#define OLED_SCL 43

// Robotistan 1.3" SH1106 OLED ekran için Yazılımsal (SW) I2C sürücüsü
U8G2_SH1106_128X64_NONAME_F_SW_I2C u8g2(U8G2_R0, /* clock=*/ OLED_SCL, /* data=*/ OLED_SDA, /* reset=*/ U8X8_PIN_NONE);

// --- Kamera Pin Tanımlamaları (ESP32-S3-WROOM-CAM) ---
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      5
#define Y9_GPIO_NUM        4
#define Y8_GPIO_NUM        6
#define Y7_GPIO_NUM        7
#define Y6_GPIO_NUM       14
#define Y5_GPIO_NUM       17
#define Y4_GPIO_NUM       21
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM       16
#define VSYNC_GPIO_NUM     1
#define HREF_GPIO_NUM      2
#define PCLK_GPIO_NUM     15
#define SIOD_GPIO_NUM      8
#define SIOC_GPIO_NUM      9

// --- WiFi Ayarları ---
// Arduino IDE'de yuklemeden once kendi ag bilgilerinizi girin
const char *ssid     = "WIFI_SSID_BURAYA";
const char *password = "WIFI_SIFRE_BURAYA";

// --- OpenCV ve Standart Stream Sınır Tanımı ---
#define STREAM_BOUNDARY "123456789000000000000987654321"
httpd_handle_t ozel_camera_httpd = NULL;

// --- Web Server Stream Handler ---
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t *_jpg_buf = NULL;
  char *part_buf[128];

  // Python OpenCV/urllib kütüphanelerinin tam uyumla çözdüğü standart boundary başlığı
  res = httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=" STREAM_BOUNDARY);
  if (res != ESP_OK) return res;

  // CORS politikaları için erişim izni
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Kamera kare alamadi");
      res = ESP_FAIL;
    } else {
      if (fb->format != PIXFORMAT_JPEG) {
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
        esp_camera_fb_return(fb);
        fb = NULL;
        if (!jpeg_converted) {
          Serial.println("JPEG donusum hatasi");
          res = ESP_FAIL;
        }
      } else {
        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;
      }
    }

    if (res == ESP_OK) {
      // Python'ın aradığı standart multipart ayracı (-- ile başlar)
      size_t hlen = snprintf((char *)part_buf, 128, "--" STREAM_BOUNDARY "\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", _jpg_buf_len);
      res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, "\r\n", 2);
    }

    if (fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if (_jpg_buf) {
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    if (res != ESP_OK) break;
  }
  return res;
}

// --- Web Sunucusunu Başlatma ---
void startOzelCameraServer() {
  httpd_config_t config_server = HTTPD_DEFAULT_CONFIG();
  config_server.server_port = 80; // Python tarafındaki standart port uyumu için 80

  httpd_uri_t stream_uri = {
    .uri       = "/", // Kök dizin (http://IP_ADRESI/)
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };

  if (httpd_start(&ozel_camera_httpd, &config_server) == ESP_OK) {
    httpd_register_uri_handler(ozel_camera_httpd, &stream_uri);
    Serial.println("[ESP32] Kamera sunucusu basariyla baslatildi.");
  }
}

// --- Setup Fonksiyonu ---
void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  // 1. Ekran Kurulumu ve Açılış Logu
  u8g2.begin();
  u8g2.setI2CAddress(0x3C * 2);
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.drawStr(0, 15, "Sistem Baslatiliyor...");
  u8g2.drawStr(0, 35, "WiFi Baglaniyor...");
  u8g2.sendBuffer();

  // 2. Kamera Konfigürasyonu
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;

  // YOLO modelinin görüntüyü rahat ve hızlı işlemesi için ideal çözünürlük (VGA)
  config.frame_size = FRAMESIZE_VGA;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 2; // Çift frame buffer ile akıcı yayın

  // Kamera Başlatma Kontrolü
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Kamera hatasi: 0x%x\n", err);
    u8g2.clearBuffer();
    u8g2.drawStr(0, 30, "Kamera Hatasi!");
    u8g2.sendBuffer();
    return;
  }

  // WiFi Bağlantısı
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Baglandi.");

  // Sunucuyu Çalıştır
  startOzelCameraServer();

  // IP Adresini Konsola Yazdır
  Serial.print("Kamera Yayini Hazir! Adres: http://");
  Serial.println(WiFi.localIP());

  // IP Adresini Ekrana Basıp Sabit Bırakıyoruz (Loop içinde işlemciyi yormamak için)
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x10_tf);
  u8g2.drawStr(0, 15, "SmartWalk: AKTIF");
  u8g2.drawStr(0, 35, "IP:");
  u8g2.drawStr(25, 35, WiFi.localIP().toString().c_str());
  u8g2.drawStr(0, 55, "YOLO Baglantisi Bekliyor");
  u8g2.sendBuffer();
}

// --- Loop Fonksiyonu ---
void loop() {
  // Loop içi tamamen boş ve hiyerarşiyi tıkamıyor.
  // Tüm işlemci gücü arka planda pürüzsüz kamera yayınına aktarılıyor.
  delay(10);
}

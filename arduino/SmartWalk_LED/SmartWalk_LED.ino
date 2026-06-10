/*
 * SmartWalk — Arduino LED Kontrol Kodu
 *
 * Python'dan seri port üzerinden:
 *   '1' gelirse → Kırmızı LED yak (İhlal)
 *   '0' gelirse → LED söndür (Güvenli)
 *
 * Bağlantı: Arduino USB ile bilgisayara bağlı
 * Baud rate: 9600
 */

int kirmiziLED = 13; // Dahili LED veya pine bağladığın LED

void setup() {
  Serial.begin(9600);
  pinMode(kirmiziLED, OUTPUT);
  digitalWrite(kirmiziLED, LOW);
  Serial.println("SmartWalk LED hazir.");
}

void loop() {
  if (Serial.available() > 0) {
    char komut = Serial.read();

    if (komut == '1') {
      digitalWrite(kirmiziLED, HIGH); // Ihlal — LED yak
    }
    else if (komut == '0') {
      digitalWrite(kirmiziLED, LOW);  // Guvenli — LED sondur
    }
  }
}

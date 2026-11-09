#include <Arduino.h>

// Sketch kiem tra rieng. KHONG phai firmware chay xe.
// Dung mapping8chan motor da xac nhan trong du an.
const uint8_t MOTOR_PINS[] = {44, 3, 5, 9, 7, 8, 11, 12};
unsigned long lastReport = 0;

void forceMotorStop() {
  for (uint8_t i = 0; i < sizeof(MOTOR_PINS) / sizeof(MOTOR_PINS[0]); ++i) {
    digitalWrite(MOTOR_PINS[i], LOW);
    pinMode(MOTOR_PINS[i], OUTPUT);
    analogWrite(MOTOR_PINS[i], 0);
  }
}

void setup() {
  forceMotorStop();
  Serial.begin(115200);
  Serial.println("MOTOR_LOCK_V1 READY - ignoring all drive commands");
}

void loop() {
  forceMotorStop();
  if (millis() - lastReport >= 1000) {
    lastReport = millis();
    Serial.print("MOTOR_LOCK_V1 up_ms=");
    Serial.print(millis());
    Serial.println(" requested_PWM=0 on 44,3,5,9,7,8,11,12");
  }
  delay(10);
}

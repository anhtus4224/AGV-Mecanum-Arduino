// Mega 2560: kiem tra 4 thanh, KHONG dieu khien xe chay.
const uint8_t MOTOR_PINS[] = {44, 3, 5, 9, 7, 8, 11, 12};
const uint8_t FRONT_PINS[] = {A0, A1, A2, A3, A4};
const uint8_t RIGHT_PINS[] = {A11, A12, A13, A14, A15};
const uint8_t BACK_PINS[] = {A6, A7, A8, A9, A10};
const uint8_t LEFT_PINS[] = {32, 33, 34, 35, 36};

void initBar(const uint8_t* pins) {
  for (uint8_t i = 0; i < 5; i++) pinMode(pins[i], INPUT);
}

void printBar(const char* name, const uint8_t* pins) {
  int raw[5];
  for (uint8_t i = 0; i < 5; i++) raw[i] = digitalRead(pins[i]);
  Serial.print(name);
  Serial.print(" RAW=");
  for (uint8_t i = 0; i < 5; i++) Serial.print(raw[i] == HIGH ? '1' : '0');
  Serial.print(" LINE=");
  for (uint8_t i = 0; i < 5; i++) Serial.print(raw[i] == LOW ? '1' : '0');
  Serial.println();
}

void setup() {
  for (uint8_t i = 0; i < 8; i++) {
    digitalWrite(MOTOR_PINS[i], LOW);
    pinMode(MOTOR_PINS[i], OUTPUT);
    analogWrite(MOTOR_PINS[i], 0);
  }
  Serial.begin(115200);
  initBar(FRONT_PINS);
  initBar(RIGHT_PINS);
  initBar(BACK_PINS);
  initBar(LEFT_PINS);
  Serial.println("TEST_4_THANH - OUTPUT MOTOR=0 - OUT1..OUT5");
}

void loop() {
  printBar("F", FRONT_PINS);
  printBar("R", RIGHT_PINS);
  printBar("B", BACK_PINS);
  printBar("L", LEFT_PINS);
  Serial.println();
  delay(250);
}

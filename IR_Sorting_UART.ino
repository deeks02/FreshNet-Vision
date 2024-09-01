#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Define pins for IR sensors
const int SmallgatePin = 3;
const int MediumgatePin = 4;
const int LargegatePin = 5;

// Servo constants
#define SERVOMIN 150
#define SERVOMAX 600

// Create an instance of the Adafruit_PWMServoDriver class
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// Size and match input from Raspberry Pi
char size;
char speciesMatch;
char mot;

// DC motor control pins
const int enA = 9;
const int in1 = 10;
const int in2 = 11;

// Function to sort fish based on size
void sortFish(const char fishSize) {
  if (fishSize == 's') {
    if (digitalRead(SmallgatePin) == LOW) {
        // Trigger gate open/close with non-blocking delay
        openCloseGate(0,120);
        unsigned long startTime = millis();
        while (millis() - startTime < 500);
    }
  } else if (fishSize == 'm') {
      if (digitalRead(MediumgatePin) == LOW) {
        // Trigger gate open/close with non-blocking delay
        openCloseGate(1,60);
        unsigned long startTime = millis();
        while (millis() - startTime < 500);
    }
  } else if (fishSize == 'l') {
    if (digitalRead(LargegatePin) == LOW) {
      // Trigger gate open/close with non-blocking delay
      openCloseGate(2,120);
      unsigned long startTime = millis();
      while (millis() - startTime < 500);
    }
  } else {
    closeAllgates();
  }
}

// Function to open and close the gate with non-blocking delay
void openCloseGate(int gatePin, int angle) {
  rotateServo(gatePin, angle); // Open the gate
  unsigned long startTime = millis();
  while (millis() - startTime < 1000);
  if(gatePin == 1) {
    rotateServo(gatePin, 0); // Close the gate
  } else {
    rotateServo(gatePin, 180); // Close the gate
  }

}

// Function to rotate a servo to a specific angle
void rotateServo(uint8_t pin, uint16_t angle) {
  uint16_t pulse_width = map(angle, 0, 180, SERVOMIN, SERVOMAX);
  pwm.setPWM(pin, 0, pulse_width);
}

void closeAllgates() {
  rotateServo(0, 180);
  rotateServo(1, 0);
  rotateServo(2, 180);
}

void setup() {
  Serial.begin(9600); // Initialize serial communication at 9600 baud rate
  // Initialize PCA9685 board
  pwm.begin();
  pwm.setPWMFreq(60);
  // Initialize IR sensor pins
  pinMode(SmallgatePin, INPUT);
  pinMode(MediumgatePin, INPUT);
  pinMode(LargegatePin, INPUT);
  // DC motor pins
  pinMode(enA, OUTPUT);
  pinMode(in1, OUTPUT);
  pinMode(in2, OUTPUT);
  // Turn off DC motor initially
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
}

void loop() {
  // Check if data is available in the serial buffer
  while (Serial.available() > 0) {
    char incomingChar = Serial.read();
    
    // Check if the character is species match data
    if (incomingChar == 't' || incomingChar == 'f') {
      speciesMatch = incomingChar;
    }
    // Check if the character is size data
    else if (incomingChar == 's' || incomingChar == 'm' || incomingChar == 'l') {
      size = incomingChar;
    }
    // Check if the character is motor control data
    else if (incomingChar == '0' || incomingChar == '1') {
      mot = incomingChar;
    }
    // Ignore other characters
  }

  // Process the received data as needed
  if (speciesMatch == 't'){
    if (size == 's' || size == 'm' || size == 'l') {
      if (digitalRead(SmallgatePin) == LOW || digitalRead(MediumgatePin) == LOW || digitalRead(LargegatePin) == LOW) {
        // Sort the fish based on size and species match (data already read)
        sortFish(size);
      } 
    } else {
      closeAllgates();
    }
  } else {
    closeAllgates();
  }

  // Motor control
  if (mot == '1') {
    // Start DC motor
    digitalWrite(in1, HIGH);
    digitalWrite(in2, LOW);
    analogWrite(enA, 220);
  } else if (mot == '0') {
    // Stop DC motor
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
  }
}

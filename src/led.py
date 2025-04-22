import RPi.GPIO as GPIO
from logit import log
from gpio import BUTTON_LED_PIN, STAGE_LEDS

def turn_on_all_leds():
    """Turn on all LEDs (button and stage LEDs)"""
    try:
        # Turn on all stage LEDs
        for color, pin in STAGE_LEDS.items():
            GPIO.output(pin, GPIO.HIGH)
            log(f"Turned on {color} LED at pin {pin}")
        # Turn on button LED
        GPIO.output(BUTTON_LED_PIN, GPIO.HIGH)
        log("All LEDs turned on")
    except Exception as e:
        log(f"Error turning on all LEDs: {e}")

def turn_off_all_leds():
    """Turn off all LEDs (button and stage LEDs)"""
    try:
        # Turn off all stage LEDs
        for color, pin in STAGE_LEDS.items():
            GPIO.output(pin, GPIO.LOW)
            log(f"Turned off {color} LED at pin {pin}")
        # Turn off button LED
        GPIO.output(BUTTON_LED_PIN, GPIO.LOW)
        log("All LEDs turned off")
    except Exception as e:
        log(f"Error turning off all LEDs: {e}")

def turn_on_stage_led(stage):
    """Turn on only the LED for a specific stage"""
    try:
        # Turn off all LEDs first
        turn_off_all_leds()
        # Turn on the specific stage LED
        if stage in STAGE_LEDS:
            GPIO.output(STAGE_LEDS[stage], GPIO.HIGH)
            log(f"Stage LED turned on for {stage}")
    except Exception as e:
        log(f"Error turning on stage LED: {e}")

def turn_on_button_led():
    """Turn on the button LED"""
    try:
        GPIO.output(BUTTON_LED_PIN, GPIO.HIGH)
        log("Button LED turned on")
    except Exception as e:
        log(f"Error turning on button LED: {e}")

def turn_off_button_led():
    """Turn off the button LED"""
    try:
        GPIO.output(BUTTON_LED_PIN, GPIO.LOW)
        log("Button LED turned off")
    except Exception as e:
        log(f"Error turning off button LED: {e}")

def cleanup():
    """Clean up GPIO resources"""
    GPIO.cleanup() 
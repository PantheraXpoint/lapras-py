package kr.ac.kaist.cdsn.lapras.agents.shade;

import com.pi4j.io.gpio.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Created by JWP on 2017. 8. 7.
 *
 */
public class ShadeSwitch {
    private static final Logger LOGGER = LoggerFactory.getLogger(ShadeSwitch.class);

    private final GpioController gpioController = GpioFactory.getInstance();
    private final GpioPinDigitalOutput switchPin;

    public ShadeSwitch(String pinName) {
        Pin gpioPin = RaspiPin.getPinByName(pinName);
        this.switchPin = gpioController.provisionDigitalOutputPin(gpioPin, pinName, PinState.HIGH);
    }

    public final void switchOn() throws InterruptedException {
        this.switchPin.setState(PinState.LOW);
        Thread.sleep(50);
        this.switchPin.setState(PinState.HIGH);
    }
}

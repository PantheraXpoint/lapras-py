package kr.ac.kaist.cdsn.lapras.agents.light;

import com.pi4j.io.gpio.*;

/**
 * @auther Sanghoon Yoon (iDBLab, shygiants@gmail.com)
 * @date 2016. 7. 2.
 * @see
 */
public class RelayLight extends Light {

    private final GpioController gpioController = GpioFactory.getInstance();
    private final GpioPinDigitalOutput powerPin;

    public RelayLight(Pin powerPin) {
        logger.info("Created");
        this.powerPin = gpioController.provisionDigitalOutputPin(powerPin, "RelayPin", PinState.HIGH);
    }

    @Override
    public void setOnOff(boolean state) {
        do {
            powerPin.setState(!state);
        } while (powerPin.getState() != (state? PinState.LOW : PinState.HIGH));
    }
}

package kr.ac.kaist.cdsn.lapras.agents.light;

import com.pi4j.io.gpio.*;
import com.pi4j.io.gpio.event.GpioPinDigitalStateChangeEvent;
import com.pi4j.io.gpio.event.GpioPinListenerDigital;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @auther Sanghoon Yoon (iDBLab, shygiants@gmail.com)
 * @date 2016. 7. 13.
 * @see
 */
public class LivoloSwitch implements GpioPinListenerDigital {

    public interface OnClickListener {
        void onClick(int buttonNum);
    }

    private static final Logger logger = LoggerFactory.getLogger(LivoloSwitch.class);

    private final GpioController gpioController = GpioFactory.getInstance();

    private final GpioPinDigitalInput button2;
    private final GpioPinDigitalInput button3;

    private final GpioPinDigitalInput pin2;
    private final GpioPinDigitalInput pin3;

    private boolean button2IsRed;
    private boolean button3IsRed;

    private final OnClickListener listener;

    public LivoloSwitch(OnClickListener listener) {
        logger.info("Created");

        this.listener = listener;

        button2 = gpioController.provisionDigitalInputPin(RaspiPin.GPIO_00, "Button2");
        button3 = gpioController.provisionDigitalInputPin(RaspiPin.GPIO_02, "Button3");
        button2IsRed = button2.isHigh();
        button3IsRed = button3.isHigh();

        pin2 = gpioController.provisionDigitalInputPin(RaspiPin.GPIO_21, "Pin2");
        pin3 = gpioController.provisionDigitalInputPin(RaspiPin.GPIO_22, "Pin3");

        button2.addListener(this);
        button3.addListener(this);

        pin2.addListener(this);
        pin3.addListener(this);
    }

    @Override
    public void handleGpioPinDigitalStateChangeEvent(GpioPinDigitalStateChangeEvent event) {
        // Called when signal come from GPIO
        GpioPin pin = event.getPin();
        String pinName = pin.getName();
        PinState state = event.getState();
        logger.debug("Pin {}: State: {}", pin, state);

        // Need to be synchronized since this callback is called by multiple GPIO threads
        synchronized (signalBuf) {
            if (!signalBuf.isStarted) {
                signalBuf.start();
                new Thread(new InterruptHandler()).start();
            }
            switch (pinName) {
                case "Button2":
                    signalBuf.onButton2(state.isHigh());
                    break;
                case "Button3":
                    signalBuf.onButton3(state.isHigh());
                    break;
            }
        }
    }

    private final SignalBuf signalBuf = new SignalBuf();

    // Buffers signals for a short time and find which button is touched by analyzing those signals
    private class SignalBuf {

        private boolean isStarted = false;
        private boolean button2IsChanged = false;
        private boolean button3IsChanged = false;

        public void onButton2(boolean isHigh) {
            button2IsChanged = button2IsRed != isHigh;
        }

        public void onButton3(boolean isHigh) {
            button3IsChanged = button3IsRed != isHigh;
        }

        public void start() {
            isStarted = true;
        }

        public int findBtnTouched() {
            int btnTouched;
            if (button2IsChanged) {
                button2IsRed = !button2IsRed;
                btnTouched = 2;
            } else if (button3IsChanged) {
                button3IsRed = !button3IsRed;
                btnTouched = 3;
            } else {
                btnTouched = 1;
            }

            button2IsRed = button2.isHigh();
            button3IsRed = button3.isHigh();

            button2IsChanged = false;
            button3IsChanged = false;
            isStarted = false;

            return btnTouched;
        }
    }

    private class InterruptHandler implements Runnable {

        @Override
        public void run() {
            logger.debug("Start Livolo interrupt handler");
            try {
                // Collect signals for a short time
                Thread.sleep(100);
            } catch (Exception e) {
                e.printStackTrace();
            }

            int btnTouched;
            synchronized (signalBuf) {
                btnTouched = signalBuf.findBtnTouched();
            }
            logger.info("Button{} Touched!", btnTouched);
            // Notify which button is touched
            listener.onClick(btnTouched);
            logger.debug("End Livolo interrupt handler");
        }
    }
}

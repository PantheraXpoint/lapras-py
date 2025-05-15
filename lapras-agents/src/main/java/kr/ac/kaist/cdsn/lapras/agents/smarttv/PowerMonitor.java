package kr.ac.kaist.cdsn.lapras.agents.smarttv;

import com.phidgets.InterfaceKitPhidget;
import com.phidgets.PhidgetException;

import java.text.SimpleDateFormat;
import java.util.Date;


/**
 * Monitors the power on/off of the smarttv using the Phidget light sensor.
 * The state change is updated to the SmartboardState class.
 *
 * @author Heesuk Son (heesuk.son@kaist.ac.kr), Byoungheon Shin
 *         (bhshin@kaist.ac.kr)
 *
 */
public class PowerMonitor extends Thread {
    // private final int PHIDGET_SERIAL_NO = 175473; // the serial number of the
    // Phidget interface kit
    private final int PHIDGET_SERIAL_NO = -1;
    private final int LIGHT_SENSOR_INDEX = 7; // index of the attached light
    // sensor in the Phidget
    // interface kit
    private int[] check;
    private final int TURNEDON = 0;
    private final int TURNEDOFF = 1;
    private final int NOCHANGE = 2;
    private static InterfaceKitPhidget phidget = null;

    private boolean isRunning = false;

    private SmartboardState state; // to maintain the software state of the
    // smarttv

    public PowerMonitor() {
        // open a new Phidget interface kit with the serial number
        openInterfaceKit(PHIDGET_SERIAL_NO);

        check = new int[3];
        check[0] = 0;
        check[1] = 0;
        check[2] = 0;
        state = SmartboardState.getInstance();
    }

    /**
     * Opens a Phidget interface kit with a serial number. If no interface kit
     * is attached via USB, then this method will wait for the attachement
     * indefinitely.
     *
     * @param serialNo
     *            The serial number of the attached Phidget interface kit
     */
    private void openInterfaceKit(int serialNo) {
        try {
            phidget = new InterfaceKitPhidget();
            System.out.println(" [SBLightSensor] waiting for InterfaceKit attachment...");
            phidget.open(serialNo);
            phidget.waitForAttachment();
            System.out.println("   -attached: " + phidget.getDeviceID() + " (s/n: " + phidget.getSerialNumber() + ")");

        } catch (PhidgetException e) {
            e.printStackTrace();
        }
    }

    /**
     * Gets a sensor value of the attached Phidget interface kit. The position
     * of the light sensor should be specified as a parameter.
     *
     * @return light sensor value (-100000 if failed)
     */
    private int getLightValue() {
        int returnValue = -100000;

        if (phidget != null) {
            try {
                returnValue = phidget.getSensorValue(LIGHT_SENSOR_INDEX);
            } catch (PhidgetException e) {
                e.printStackTrace();
            }
        }

        return returnValue;
    }

    public void terminate() {
        this.isRunning = false;
    }

    public void run() {
        try {
            isRunning = true;
            while (isRunning) {
                // this.addCheck(phidget.getSensorValue(LIGHT_SENSOR_INDEX));
                this.addCheck(getLightValue());

                switch (this.state()) {
                    case TURNEDON:
                        state.setSmartboardOn(true);
                        break;
                    case TURNEDOFF:
                        state.setSmartboardOn(false);
                        break;
                    case NOCHANGE:
                        break;
                }
                Thread.sleep(500);
            }
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    private void addCheck(int value) {
        check[2] = check[1];
        check[1] = check[0];
        check[0] = value;
    }

    /**
     * Gets a state based on three recent values of the light sensor attached in
     * the smarttv
     *
     * @return smarttv status (0: TURNEDON, 1: TURNEDOFF, 2: NOCHANGE)
     */
    private int state() {
        if (check[0] > 50 && check[1] > 50 && check[2] > 50 && !state.isSmartboardOn()) {

            long time = System.currentTimeMillis();
            SimpleDateFormat dayTime = new SimpleDateFormat("yyyy-mm-dd hh:mm:ss");
            String str = dayTime.format(new Date(time));

            System.out.println(" [SB_PowerMonitor] LightSensor senses power on (" + str + ")");
            if (SmartboardState.DEBUG_SMARTBOARD) {
                System.out
                        .println("  -check[0]:" + check[0] + "\n  -check[1]:" + check[1] + "\n  -check[2]:" + check[2]);
            }
            return TURNEDON;
        } else if (check[0] < 15 && check[1] < 15 && check[2] < 15 && state.isSmartboardOn()) {
            long time = System.currentTimeMillis();
            SimpleDateFormat dayTime = new SimpleDateFormat("yyyy-mm-dd hh:mm:ss");
            String str = dayTime.format(new Date(time));
            System.out.println(" [SB_PowerMonitor] LightSensor senses power off (" + str + ")");
            if (SmartboardState.DEBUG_SMARTBOARD) {
                System.out
                        .println("  -check[0]:" + check[0] + "\n  -check[1]:" + check[1] + "\n  -check[2]:" + check[2]);
            }
            return TURNEDOFF;
        } else {
            if (SmartboardState.DEBUG_SMARTBOARD) {
                System.out.println(" [SB_PowerMonitor] no change: " + state.isSmartboardOn());
                System.out
                        .println("  -check[0]:" + check[0] + "\n  -check[1]:" + check[1] + "\n  -check[2]:" + check[2]);
            }
            return NOCHANGE;
        }
    }
}
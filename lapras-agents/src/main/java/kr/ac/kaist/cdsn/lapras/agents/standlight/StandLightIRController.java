package kr.ac.kaist.cdsn.lapras.agents.standlight;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.phidgets.IRPhidget;
import com.phidgets.PhidgetException;
import com.phidgets.event.AttachEvent;
import com.phidgets.event.AttachListener;
import com.phidgets.event.DetachEvent;
import com.phidgets.event.DetachListener;
import com.phidgets.event.ErrorEvent;
import com.phidgets.event.ErrorListener;

public class StandLightIRController {
    private static final Logger LOGGER = LoggerFactory.getLogger(StandLightIRController.class);

    private final int phidgetSerial;
    private IRPhidget irPhidget = null;

    public StandLightIRController(int phidgetSerial) {
        this.phidgetSerial = phidgetSerial;
    }

    // IR Phidget Control code from AirConditionerController

    public void start() throws PhidgetException {
        this.irPhidget = new IRPhidget();
        this.irPhidget.addAttachListener(new AttachListener() {
            @Override
            public void attached(AttachEvent ae) {
                LOGGER.info("Phidget Attached: {}", ae.toString());
            }
        });
        this.irPhidget.addDetachListener(new DetachListener() {
            @Override
            public void detached(DetachEvent de) {
                LOGGER.info("Phidget Detached: {}", de.toString());
            }
        });
        this.irPhidget.addErrorListener(new ErrorListener() {
            @Override
            public void error(ErrorEvent ee) {
                LOGGER.error("Phidget Error Event: {}", ee.toString());
            }
        });

        // Attempt to open
        LOGGER.info("Attempting to open Phidget ID: " + this.phidgetSerial);
        if (this.phidgetSerial < 0) {
            this.irPhidget.openAny();
        } else {
            this.irPhidget.open(this.phidgetSerial);
        }

        LOGGER.info("Waiting for attachment...");
        this.irPhidget.waitForAttachment();
    }

    // Transmit IR signal through Phidget 1055
    private boolean transmitRaw(int[] rawData) {
        if (this.irPhidget == null) {
            LOGGER.error("IRPhidget is not initialized.");
            return false;
        }

        try {
            this.irPhidget.transmitRaw(rawData);
            return true;
        } catch (PhidgetException e) {
            LOGGER.error(e.getMessage(), e);
        }
        return false;
    }

    public void shutdown() {
        if (this.irPhidget != null) {
            try {
                this.irPhidget.close();
            } catch (PhidgetException e) {
                LOGGER.error(e.getMessage(), e);
            }
        }
    }

    public boolean setLight(boolean lightColor, int lightLevel) {
    	if (lightColor) { // orange color
            //if (lightLevel==0) return turnOnOff();
    		if (lightLevel==1) return orangeLev1();
    		if (lightLevel==2) return orangeLev2();
    		if (lightLevel==3) return orangeLev3();
    		if (lightLevel==4) return orangeLev4();
    	} else { // white color
            //if (lightLevel==0) return turnOnOff();
    		if (lightLevel==1) return whiteLev1();
    		if (lightLevel==2) return whiteLev2();
    		if (lightLevel==3) return whiteLev3();
    		if (lightLevel==4) return whiteLev4();
    	}
    	return false;
    }

    public boolean turnOnOff() {
        return transmitRaw(ONOFF);
    }

    // Call when modifying color or brightness level of stand light
    public boolean whiteLev1() {
        return transmitRaw(WHITE_LEV1);
    }

    public boolean whiteLev2() {
        return transmitRaw(WHITE_LEV2);
    }

    public boolean whiteLev3() {
        return transmitRaw(WHITE_LEV3);
    }

    public boolean whiteLev4() { return transmitRaw(WHITE_LEV4); }

    public boolean orangeLev1() { return transmitRaw(ORANGE_LEV1); }

    public boolean orangeLev2() {
        return transmitRaw(ORANGE_LEV2);
    }

    public boolean orangeLev3() {
        return transmitRaw(ORANGE_LEV3);
    }

    public boolean orangeLev4() {
        return transmitRaw(ORANGE_LEV4);
    }

    // Values of control signal is measured as: http://wonder.kaist.ac.kr/SmartIoT/SmartIoT_2.2/issues/49#note_616
    private final static int[] ONOFF = {8960,   4550,    520,    590,    550,    580,    520,    620,    520,    590,
            540,    590,    520,    620,    520,    590,    540,    590,    520,   1720,
            550,   1720,    520,   1730,    520,   1720,    540,   1730,    520,   1720,
            530,   1720,    540,   1730,    520,    590,    550,    580,    520,    620,
            510,   1730,    520,    620,    520,    580,    560,   1710,    520,    590,
            550,   1720,    520,   1730,    520,   1720,    550,    580,    520,   1730,
            540,   1730,    510,    600,    540,   1730,    520,  40020,   8960,   2280,
            540};

    private final static int[] WHITE_LEV1 = {8960,   4550,    520,    640,    500,    610,    500,    610,    520,    590,
            540,    590,    520,    620,    520,    580,    550,    590,    520,   1770,
            500,   1770,    470,   1780,    470,   1770,    490,   1780,    470,   1770,
            470,   1770,    500,   1770,    470,    620,    520,    590,    520,    610,
            520,    590,    540,    590,    520,    620,    520,   1770,    470,    670,
            470,   1770,    470,   1770,    500,   1770,    470,   1780,    460,   1780,
            490,   1780,    470,    610,    580,   1720,    460,  40020,   9010,   2280,
            500};

    private final static int[] WHITE_LEV2 = {9010,   4500,    520,    640,    500,    610,    500,    610,    510,    600,
            540,    590,    520,    620,    520,    580,    550,    590,    520,   1770,
            500,   1770,    470,   1780,    470,   1770,    490,   1780,    470,   1770,
            470,   1780,    490,   1780,    470,    610,    520,    590,    520,   1770,
            500,    590,    510,    620,    520,    590,    550,   1770,    470,    590,
            540,   1780,    470,   1770,    470,    640,    500,   1770,    470,   1780,
            490,   1780,    470,    580,    540,   1780,    470,  40020,   9020,   2280,
            490};

    private final static int[] WHITE_LEV3 = {8960,   4550,    570,    540,    550,    590,    520,    610,    520,    590,
            540,    590,    520,    620,    520,    590,    540,    590,    520,   1720,
            550,   1720,    520,   1730,    520,   1720,    540,   1730,    520,   1720,
            520,   1720,    550,   1720,    520,    590,    550,    590,    520,   1720,
            550,    590,    520,    610,    520,    590,    540,   1730,    520,    590,
            550,   1720,    510,   1730,    520,    610,    520,   1730,    520,   1720,
            540,   1730,    520,    590,    550,   1720,    520,  40010,   8960,   2280,
            550};

    private final static int[] WHITE_LEV4 = {8980,   4530,    540,    640,    480,    610,    520,    580,    550,    590,
            520,    610,    530,    580,    550,    590,    510,    620,    520,   1780,
            460,   1780,    490,   1780,    460,   1780,    470,   1770,    500,   1770,
            470,   1770,    470,   1780,    500,   1760,    470,    620,    520,   1750,
            490,    590,    550,    580,    530,    610,    510,   1780,    470,    640,
            490,    590,    550,   1770,    480,    610,    510,   1750,    500,   1770,
            470,   1770,    500,    610,    490,   1760,    520};

    private final static int[] ORANGE_LEV1 = {8960,   4550,    520,    590,    600,    530,    570,    570,    570,    530,
            600,    540,    570,    560,    570,    540,    600,    530,    570,   1700,
            520,   1720,    530,   1710,    530,   1720,    550,   1710,    530,   1720,
            520,   1720,    540,   1730,    520,    580,    610,    530,    570,   1720,
            550,   1670,    510,    590,    600,    540,    570,   1670,    590,    540,
            580,   1670,    590,   1670,    580,    530,    600,    540,    560,   1680,
            590,   1680,    570,    530,    600,   1670,    570,  39940,   8960,   2330,
            540};

    private final static int[] ORANGE_LEV2 = {9020,   4490,    530,    640,    490,    620,    490,    610,    530,    580,
            540,    600,    510,    620,    520,    590,    550,    580,    520,   1780,
            490,   1780,    460,   1780,    470,   1770,    490,   1780,    470,   1770,
            470,   1780,    500,   1770,    460,   1780,    470,    640,    490,   1750,
            500,   1770,    490,    620,    490,    620,    520,   1750,    490,    610,
            520,    590,    550,   1750,    490,    590,    550,    590,    520,   1740,
            520,   1780,    470,    610,    520,   1750,    500};

    private final static int[] ORANGE_LEV3 = {9020,   4490,    520,    640,    500,    610,    490,    620,    520,    590,
            550,    580,    520,    620,    510,    590,    550,    590,    520,   1770,
            500,   1770,    480,   1760,    470,   1780,    500,   1770,    470,   1770,
            460,   1780,    500,   1770,    470,    610,    520,    590,    520,    610,
            520,    590,    550,   1770,    480,    610,    510,   1780,    470,    610,
            530,   1770,    470,   1770,    470,   1770,    500,   1770,    470,    610,
            520,   1750,    500,    590,    540,   1750,    500};

    private final static int[] ORANGE_LEV4 = {8960,   4550,    520,    610,    530,    580,    520,    620,    520,    580,
            550,    590,    520,    610,    520,    590,    540,    590,    530,   1770,
            490,   1780,    470,   1770,    470,   1740,    520,   1750,    490,   1750,
            490,   1780,    490,   1780,    460,   1780,    470,    610,    520,    590,
            600,    530,    570,   1730,    490,    590,    570,   1720,    500,    590,
            570,    560,    570,   1720,    470,   1720,    550,   1720,    520,    590,
            600,   1720,    470,    590,    600,   1720,    470,  39980,   8960,   2330,
            500};
}
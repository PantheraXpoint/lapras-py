package kr.ac.kaist.cdsn.lapras.agents.phidget;

import com.phidgets.IRCode;
import com.phidgets.IRCodeInfo;
import com.phidgets.IRPhidget;
import com.phidgets.PhidgetException;
import com.phidgets.event.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Created by Daekeun Lee on 2017-07-25.
 */
public class PhidgetIRController implements AttachListener, DetachListener, ErrorListener {
    private static final Logger LOGGER = LoggerFactory.getLogger(PhidgetIRController.class);

    private final IRPhidget irPhidget;

    public PhidgetIRController(int serial, CodeListener codeListener) throws PhidgetException {
        LOGGER.debug("Initializing PhidgetIR controller");
        irPhidget = new IRPhidget();

        irPhidget.addAttachListener(this);
        irPhidget.addDetachListener(this);
        irPhidget.addErrorListener(this);
        irPhidget.addCodeListener(codeListener);

        openIRPhidget(serial);
    }

    public PhidgetIRController(int serial) throws PhidgetException {
        LOGGER.debug("Initializing PhidgetIR controller");
        irPhidget = new IRPhidget();

        irPhidget.addAttachListener(this);
        irPhidget.addDetachListener(this);
        irPhidget.addErrorListener(this);

        openIRPhidget(serial);
    }

    private void openIRPhidget(int serial) throws PhidgetException {
        // Attempt to open
        LOGGER.debug("Attempting to open IRPhidget with serial: {}", serial);
        if (serial < 0) {
            irPhidget.openAny();
        } else {
            irPhidget.open(serial);
        }

        LOGGER.debug("Waiting for attachment...");
        irPhidget.waitForAttachment();
    }

    protected boolean transmit(int[] rawData) {
        try {
            if(irPhidget == null || !irPhidget.isAttached()) {
                return false;
            }
            irPhidget.transmitRaw(rawData);
            return true;
        } catch (PhidgetException e) {
            LOGGER.error(e.getMessage(), e);
            return false;
        }
    }

    protected boolean transmit(IRCode irCode, IRCodeInfo irCodeInfo) {
        try {
            irPhidget.transmit(irCode, irCodeInfo);
            return true;
        } catch (PhidgetException e) {
            LOGGER.error(e.getMessage(), e);
            return false;
        }
    }

    @Override
    public void attached(AttachEvent attachEvent) {
        LOGGER.debug("IRPhidget attached: {}", attachEvent.toString());
    }

    @Override
    public void detached(DetachEvent detachEvent) {
        LOGGER.debug("IRPhidget detached: {}", detachEvent.toString());
    }

    @Override
    public void error(ErrorEvent errorEvent) {
        LOGGER.debug("IRPhidget error occurred: {}", errorEvent.toString());
    }
}

package kr.ac.kaist.cdsn.lapras.agents.rfid;

import com.phidgets.PhidgetException;
import com.phidgets.RFIDPhidget;
import com.phidgets.event.*;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * Created by JWP on 2017. 9. 4..
 */
public class RFIDReaderAgent extends AgentComponent implements AttachListener, DetachListener, ErrorListener, TagGainListener, TagLossListener, OutputChangeListener {
    private static final Logger LOGGER = LoggerFactory.getLogger(RFIDReaderAgent.class);

    private final RFIDPhidget rfidPhidget;
    private final Map<String, String> userRFIDBandMap = new HashMap<>();
    private final Map<String, String> userRFIDCardMap = new HashMap<>();

    public RFIDReaderAgent(EventDispatcher eventDispatcher, Agent agent) throws PhidgetException {
        super(eventDispatcher, agent);

        AgentConfig agentConfig = agent.getAgentConfig();

        int serial = Integer.parseInt(agentConfig.getOption("phidget_serial"));
        String [] userNames = agentConfig.getOptionAsArray("rfid_users");
        String [] rfidBandIds = agentConfig.getOptionAsArray("rfid_band_ids");
        String [] rfidCardIds = agentConfig.getOptionAsArray("rfid_card_ids");

        assert userNames.length == rfidBandIds.length;
        assert userNames.length == rfidCardIds.length;

        for (int i=0; i<userNames.length; i++) {
            String userName = userNames[i];
            String rfidBandId = rfidBandIds[i];
            String rfidCardId = rfidCardIds[i];

            userRFIDBandMap.put(rfidBandId, userName);
            userRFIDCardMap.put(rfidCardId, userName);
        }


        LOGGER.info("User name and RFID tag IDs initialized");
        LOGGER.debug(Arrays.toString(userRFIDBandMap.entrySet().toArray()));
        LOGGER.debug(Arrays.toString(userRFIDCardMap.entrySet().toArray()));

        rfidPhidget = new RFIDPhidget();

        rfidPhidget.addAttachListener(this);
        rfidPhidget.addDetachListener(this);
        rfidPhidget.addErrorListener(this);
        rfidPhidget.addTagGainListener(this);
        rfidPhidget.addTagLossListener(this);

        openRFIDPhidget(serial);

    }

    private void openRFIDPhidget(int serial) throws PhidgetException {
        LOGGER.debug("Attempting to open RFIDPhidget with serial:{}", serial);

        if (serial <0 ) {
            rfidPhidget.openAny();
        } else {
            rfidPhidget.open(serial);

            LOGGER.debug("Waiting for attachment...");
            rfidPhidget.waitForAttachment();
        }
    }


    @Override
    public void run() {
        while(true) {
            try {
                Thread.sleep(Integer.MAX_VALUE);
            } catch (InterruptedException e) {
                break;
            }
        }
    }

    @Override
    public void attached(AttachEvent attachEvent) {
        LOGGER.debug("RFIDPhidget attached: {}", attachEvent.toString());

        try {
            ((RFIDPhidget)attachEvent.getSource()).setAntennaOn(true);
            ((RFIDPhidget)attachEvent.getSource()).setLEDOn(true);
        } catch (PhidgetException ex) { }

    }

    @Override
    public void detached(DetachEvent detachEvent) {
        LOGGER.debug("RFIDPhidget detached: {}", detachEvent.toString());
    }

    @Override
    public void error(ErrorEvent errorEvent) {
        LOGGER.debug("RFIDPhidget error occurred: {}", errorEvent.toString());
    }

    @Override
    public void outputChanged(OutputChangeEvent outputChangeEvent) {
        LOGGER.debug("RFIDPhidget output changed: {}", outputChangeEvent.toString());
    }

    /**
     *
     * @param tagGainEvent
     *
     * This method is called when the RFID tag is attached.
     */

    @Override
    public void tagGained(TagGainEvent tagGainEvent) {
        LOGGER.debug("RFIDPhidget tag gained: {}", tagGainEvent.toString());
        try {
            ((RFIDPhidget)tagGainEvent.getSource()).setLEDOn(false);
        } catch (PhidgetException e) {
            e.printStackTrace();
        }
    }

    /**
     *
     * @param tagLossEvent
     *
     * This method is called when the RFID tag is detached.
     */

    @Override
    public void tagLost(TagLossEvent tagLossEvent) {
        LOGGER.debug("RFIDPhidget tag lost: {}", tagLossEvent.toString());

        String iD = tagLossEvent.getValue();

        // Get user name
        String userName;

        if (userRFIDBandMap.containsKey(iD)) {
            userName = userRFIDBandMap.get(iD);
        } else {
            userName = userRFIDCardMap.get(iD);
        }

        // Publish user notification
        userManager.publishUserNotification(userName, agentName);

        try {
            ((RFIDPhidget)tagLossEvent.getSource()).setLEDOn(true);
        } catch (PhidgetException e) {
            e.printStackTrace();
        }

    }
}

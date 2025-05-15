package kr.ac.kaist.cdsn.lapras.agents.fan;

import com.phidgets.PhidgetException;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityMethod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Created by Daekeun Lee on 2017-05-02.
 */
public class FanAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(FanAgent.class);

    private final int phidgetSerial;
    private FanController fanController;

    @ContextField(publishAsUpdated = true) private Context fanPower;
    @ContextField(publishAsUpdated = true) private Context fanRotation;
    @ContextField(publishAsUpdated = true) private Context fanLevel;

    public FanAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        phidgetSerial = Integer.parseInt(agent.getAgentConfig().getOption("phidget_serial"));
        try {
            fanController = new FanController(phidgetSerial);
        } catch (PhidgetException e) {
            LOGGER.error("Failed to initialize fan controller", e);
        }
    }

    @FunctionalityMethod
    public void turnOnFan() {
        if(fanController.turnOnOff()) {
            fanPower.updateValue("On");
        }
    }

    @FunctionalityMethod
    public void turnOffFan() {
        if(fanController.turnOnOff()) {
            fanPower.updateValue("Off");
            fanRotation.updateValue("Off");
            fanLevel.updateValue("Off");
        }
    }

    @FunctionalityMethod
    public void turnOnFanRotation() {
        if(fanController.turnRotationOnOff()) {
            fanRotation.updateValue("On");
        }
    }

    @FunctionalityMethod
    public void turnOffFanRotation() {
        if(fanController.turnRotationOnOff()) {
            fanRotation.updateValue("Off");
        }
    }

    @FunctionalityMethod
    public void setFanLevelHigh() {
        if(fanPower.getValue().equals("On")) { // Not yet implemented
            fanLevel.updateValue("High");
        }
    }

    @FunctionalityMethod
    public void setFanLevelMedium() {
        if(fanPower.getValue().equals("On")) { // Not yet implemented
            fanLevel.updateValue("Medium");
        }
    }

    @FunctionalityMethod
    public void setFanLevelLow() { // Not yet implemented
        if(fanPower.getValue().equals("On")) {
            fanLevel.updateValue("Low");
        }
    }

    private void publishInitialState() {
        turnOffFan();
    }

    @Override
    public void run() {
        publishInitialState();

        while(true) {
            try {
                Thread.sleep(Integer.MAX_VALUE);
            } catch (InterruptedException e) {
                break;
            }
        }
    }
}

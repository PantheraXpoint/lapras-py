package kr.ac.kaist.cdsn.lapras.agents.airpurifier;

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
 * Created by Daekeun Lee on 2017-05-01.
 *
 * Control an air purifier by PhidgetIR controller.
 *
 * Required configuration entries
 *     phidget_serial: PhidgetIR serial number
 *
 * Publishing contexts
 *     AirPurifierPower (String): Indicates whether the air purifier is on ("On") or off ("Off").
 *
 * Exposed functionalities
 *     TurnOnAirPurifier: Turn on the power of air purifier; changes AirPurifierPower context
 *     TurnOffAirPurifier: Turn off the power of air purifier; changes AirPurifierPower context
 */
public class AirPurifierAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(AirPurifierAgent.class);

    private AirPurifierController controller = null;

    public AirPurifierAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        int serial = Integer.parseInt(agent.getAgentConfig().getOption("phidget_serial"));
        try {
            controller = new AirPurifierController(serial);
        } catch (PhidgetException e) {
            LOGGER.error(e.getMessage(), e);
        }
    }

    @ContextField(publishAsUpdated = true)
    private Context airPurifierPower;

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

    @FunctionalityMethod
    public void turnOnAirPurifier() {
        LOGGER.debug("TurnOnAirPurifier called");
        if (airPurifierPower.getValue().equals("On")) return ;

        if (controller.turnOn()) {
            airPurifierPower.updateValue("On");
            actionManager.taken("TurnOnAirPurifier");
        }
    }

    @FunctionalityMethod
    public void turnOffAirPurifier() {
        LOGGER.debug("TurnOffAirPurifier called");
        if (airPurifierPower.getValue().equals("Off")) return ;

        if (controller.turnOff()) {
            airPurifierPower.updateValue("Off");
            actionManager.taken("TurnOffAirPurifier");
        }
    }
}

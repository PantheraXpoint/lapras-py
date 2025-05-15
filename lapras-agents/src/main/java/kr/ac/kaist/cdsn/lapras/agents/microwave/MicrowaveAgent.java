package kr.ac.kaist.cdsn.lapras.agents.microwave;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.agents.phidget.PhidgetSensorAgent;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityMethod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
/**
 * Created by hyunju on 2018-05-08.
 */

public class MicrowaveAgent extends PhidgetSensorAgent {
    private static final Logger LOGGER = LoggerFactory.getLogger(MicrowaveAgent.class);
    private static boolean flag_open=false;
    @ContextField(publishAsUpdated = true)
    private Context microwavestate;
   // String sensorName = agent.getAgentConfig().getOption("sensor_name");
    String threshold = agent.getAgentConfig().getOption("threshold");
    public MicrowaveAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);
        microwavestate.setInitialValue("Close");
    }

    @Override
    public void setUp() {
        super.setUp();
        microwavestate.setInitialValue("Close");
    }

    @Override
    public void valueChanged(int sensorIndex, int sensorValue) {
        LOGGER.debug("Microwave raw value read: {}", sensorValue);
       if(sensorValue>=Integer.parseInt(threshold) && flag_open==false){
           microwavestate.updateValue("Open");
           flag_open=true;
       }
       else if(sensorValue<Integer.parseInt(threshold)&& flag_open==true){
           microwavestate.updateValue("Close");
           flag_open=false;
       }

    }
    @FunctionalityMethod
    public void changeState() {
        microwavestate.updateValue(flag_open?"Open":"Close");
        if(flag_open)flag_open=false;
        else flag_open=true;

    }


}
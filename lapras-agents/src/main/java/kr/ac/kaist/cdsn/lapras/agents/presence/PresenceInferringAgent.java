package kr.ac.kaist.cdsn.lapras.agents.presence;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;

/**
 * Created by JWP on 2018. 3. 22.
 * This agent infers presence in the room using Monnit IR sensors
 */
public class PresenceInferringAgent extends AgentComponent{
    private static final Logger LOGGER = LoggerFactory.getLogger(PresenceInferringAgent.class);
    private static final Map<String, Boolean> motionContextMap = new HashMap<>();
    //private static final Map<String, Boolean> tiltAirconContextMap = new HashMap<>(); // 05/20 Kingberly
    @ContextField(publishAsUpdated = true)
    public Context inferredPresence;

    public PresenceInferringAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        String[] motion_contexts = agent.getAgentConfig().getOptionAsArray("subscribe_contexts");

        for (String motion : motion_contexts) { // Initialize motion context
            motionContextMap.put(motion, false);
        }

        inferredPresence.updateValue(false);
    }

    @Override
    protected boolean handleEvent(Event event) {
        super.handleEvent(event); //For handling event in super class (AgentComponent)
        switch(event.getType()) {
            case SUBSCRIBE_TOPIC_REQUESTED:
                break;
            case PUBLISH_MESSAGE_REQUESTED:
                break;
            case MESSAGE_ARRIVED:
                break;
            case CONTEXT_UPDATED:
                ContextInstance context = (ContextInstance) event.getData();

                if (context.getName().contains("Mtest")) { // check it is from Monnit motion sensor,
                    // To-do: Monnit motion sensor context naming
                    motionContextMap.put(context.getName(), (Boolean)context.getValue());
                    if (context.getValue().equals(true)) { // if there's any motion

                        if (inferredPresence.getValue().equals(false)) {
                            inferredPresence.updateValue(true);
                        }
                    }
                    else { // if all motion context is false.. -> false
                        Boolean allFalse = false;
                        for (Map.Entry<String, Boolean> entry : motionContextMap.entrySet()) {
                            allFalse |= entry.getValue();
                        }

                        if (!allFalse) {
                            if (inferredPresence.getValue().equals(true)) {
                                inferredPresence.updateValue(false);
                            }
                        }
                    }
                }
                    LOGGER.debug("Motion Context map: {}", motionContextMap);

                return true;
            case ACTION_TAKEN:
                break;
            case TASK_NOTIFIED:
                break;
            case TASK_INITIATED:
                break;
            case TASK_TERMINATED:
                break;
            case USER_NOTIFIED:
                break;
        }
        return false;
    }

    @Override
    public void run() {

        try {
            while(true) {
                Thread.sleep(Integer.MAX_VALUE);
            }
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }
}

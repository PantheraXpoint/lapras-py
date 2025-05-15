package kr.ac.kaist.cdsn.lapras.agents;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.LaprasException;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.communicator.LaprasTopic;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import kr.ac.kaist.cdsn.lapras.task.TaskNotification;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Created by JWP on 2017. 7. 10..
 */
public class IdleTaskDetectorAgent extends AgentComponent{
    private static final Logger LOGGER = LoggerFactory.getLogger(IdleTaskDetectorAgent.class);
    private static final long PRESENCE_CHECK_INTERVAL = 1 * 60 * 1000;

    private static List<String> presenseHistory = new ArrayList<>();
    private static String currentPresence = null;

    public IdleTaskDetectorAgent(EventDispatcher eventDispatcher, Agent agent) throws LaprasException {
        super(eventDispatcher, agent);
    }

    @ContextField
    private Context inferredUserPresence;

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.CONTEXT_UPDATED);
        subscribeEvent(EventType.TASK_NOTIFIED); // For Test
    }

    @Override
    protected boolean handleEvent(Event event) {
        switch (event.getType()) {
            case CONTEXT_UPDATED:
                ContextInstance context = (ContextInstance) event.getData();
                if (context.getName().equals("InferredUserPresence")) {
                    currentPresence = (String) context.getValue();
                    LOGGER.info("Current presence:" + currentPresence);
                }
        }
        return true;
    }

    /**
     * Check whether the current state is idle using the history of user presence.
     * If the state is idle, notify it to other agents to turn off themselves.
     */

    @Override
    public void run() {
        while (true) {
            if (currentPresence != null) {
                presenseHistory.add(currentPresence);
            }

            int historyLength = presenseHistory.size();

            if (historyLength > 10 && currentPresence.equals("present")) {
                List <String> lastPresence = presenseHistory.subList(Math.max(historyLength - 10, 0), historyLength);

                for (String element : lastPresence) {
                    if (!element.equals("present"))
                        break;

                    notifyTaskIdle();
                }
            }

            if (historyLength > 1000)
                presenseHistory.clear();

            try {
                Thread.sleep(PRESENCE_CHECK_INTERVAL);
            } catch (InterruptedException e) {
                break;
            }
        }
    }

    /**
     * Publish notifying message
     */

    private void notifyTaskIdle() {
        LOGGER.info(presenseHistory.toString());
        LOGGER.info("Current task is Idle");

        long timestamp = System.currentTimeMillis();
        List <String> involvedAgents = Arrays.asList(agent.getAgentConfig().getOptionAsArray("involved_agents"));

        LaprasTopic topic = new LaprasTopic(null, MessageType.TASK, "Idle");
        TaskNotification taskNotification = new TaskNotification("Idle", timestamp, agentName, involvedAgents);

        mqttCommunicator.publish(topic, taskNotification);
    }
}

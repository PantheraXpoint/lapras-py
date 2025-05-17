package kr.ac.kaist.cdsn.lapras.action;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.communicator.LaprasTopic;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;
import kr.ac.kaist.cdsn.lapras.communicator.MqttCommunicator;
import kr.ac.kaist.cdsn.lapras.communicator.MqttTopic;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Created by Daekeun Lee on 2016-11-24.
 */
public class ActionManager extends Component {
    private final String agentName;
    private final MqttCommunicator mqttCommunicator;

    private final Map<String, ActionInstance> latestActionMap = new ConcurrentHashMap<>();

    public ActionManager(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        this.agentName = agent.getAgentConfig().getAgentName();
        this.mqttCommunicator = agent.getMqttCommunicator();
    }

    @Override
    public void setUp() {
        mqttCommunicator.subscribeTopic(new LaprasTopic(null, MessageType.ACTION, MqttTopic.MULTILEVEL_WILDCARD));
    }

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.MESSAGE_ARRIVED);
        subscribeEvent(EventType.ACTION_TAKEN);
    }

    @Override
    protected boolean handleEvent(Event event) {
        switch(event.getType()) {
            case MESSAGE_ARRIVED: {
                LaprasTopic topic = (LaprasTopic) ((Object[]) event.getData())[0];
                if(topic.getMessageType() != MessageType.ACTION) return true;
                byte[] payload = (byte[]) ((Object[]) event.getData())[1];
                ActionInstance actionInstance = ActionInstance.fromPayload(payload);
                if(actionInstance != null) {
                    dispatchEvent(EventType.ACTION_TAKEN, actionInstance);
                }
                return true;
            }
            case ACTION_TAKEN: {
                ActionInstance actionInstance = (ActionInstance) event.getData();

                ActionInstance latestAction = latestActionMap.get(actionInstance.getName());
                if (latestAction == null || latestAction.getTimestamp() < actionInstance.getTimestamp()) {
                    latestActionMap.put(actionInstance.getName(), actionInstance);

                    if(actionInstance.getPublisher().equals(agentName)) {
                        LaprasTopic topic = new LaprasTopic(null, MessageType.ACTION, actionInstance.getName());
                        mqttCommunicator.publish(topic, actionInstance);
                    }
                }
                return true;
            }
        }
        return false;
    }

    public void taken(String actionName) {
        ActionInstance actionInstance = new ActionInstance(actionName, System.currentTimeMillis(), agentName);
        dispatchEvent(EventType.ACTION_TAKEN, actionInstance);
    }
}

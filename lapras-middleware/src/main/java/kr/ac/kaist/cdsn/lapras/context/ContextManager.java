package kr.ac.kaist.cdsn.lapras.context;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.communicator.LaprasTopic;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;
import kr.ac.kaist.cdsn.lapras.communicator.MqttCommunicator;
import kr.ac.kaist.cdsn.lapras.communicator.MqttTopic;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.*;

/**
 * Created by Daekeun Lee on 2016-11-14.
 */
public class ContextManager extends Component {
    private static Logger LOGGER = LoggerFactory.getLogger(ContextManager.class);

    private final ScheduledExecutorService periodicPublisher = Executors.newScheduledThreadPool(1);
    private final MqttCommunicator mqttCommunicator;
    private final ConcurrentMap<String, ContextInstance> contextMap = new ConcurrentHashMap<>();
    private final Set<String> contextsPublishedAsUpdated = new CopyOnWriteArraySet<>();

    public ContextManager(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);
        this.mqttCommunicator = agent.getMqttCommunicator();
    }

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.MESSAGE_ARRIVED);
    }

    @Override
    protected boolean handleEvent(Event event) {
        switch (event.getType()) {
            case MESSAGE_ARRIVED:
                LaprasTopic topic = (LaprasTopic) ((Object[])event.getData())[0];
                byte[] payload = (byte[]) ((Object[])event.getData())[1];
                if(!topic.getMessageType().equals(MessageType.CONTEXT)) break;
                ContextInstance contextInstance = ContextInstance.fromPayload(payload);
                if(contextInstance == null) break;

                LOGGER.debug("Context message arrived (name={}, value={}, timestamp={}, publisher={})",
                        contextInstance.getName(), contextInstance.getValue(), contextInstance.getTimestamp(), contextInstance.getPublisher());
                updateContext(contextInstance);
                return true;
        }
        return true;
    }

    public void publishContext(String contextName, boolean refreshTimestamp) {
        ContextInstance contextInstance = contextMap.get(contextName);
        if(contextInstance == null) return;

        if(refreshTimestamp) contextInstance.setTimestamp(System.currentTimeMillis());

        LOGGER.info("Publishing contextInstance {} = {}", contextName, contextInstance.getValue());
        LaprasTopic topic = new LaprasTopic(null, MessageType.CONTEXT, contextName);
        mqttCommunicator.publish(topic, contextInstance);
    }

    public void publishContext(String contextName) {
        publishContext(contextName, false);
    }

    public void subscribeContext(String contextName) {
        LaprasTopic topic;
        if (contextName == null) {
            LOGGER.info("Subscribing to all contexts");
            topic = new LaprasTopic(null, MessageType.CONTEXT, MqttTopic.SINGLELEVEL_WILDCARD);
        } else {
            LOGGER.info("Subscribing to context {}", contextName);
            topic = new LaprasTopic(null, MessageType.CONTEXT, contextName);
        }
        mqttCommunicator.subscribeTopic(topic);
    }

    public void updateContext(String contextName, Object contextValue, String publisher) {
        long timestamp = System.currentTimeMillis(); // Assuming that all devices are set to the same timezone
        ContextInstance contextInstance = new ContextInstance(contextName, contextValue, timestamp, publisher);
        updateContext(contextInstance);
    }

    public void updateContext(String contextName, Object contextValue, String publisher, Long timestamp) {
        ContextInstance contextInstance = new ContextInstance(contextName, contextValue, timestamp, publisher);
        updateContext(contextInstance);
    }

    private void updateContext(ContextInstance contextInstance) {
        ContextInstance formerContextInstance = contextMap.get(contextInstance.getName());
        if(formerContextInstance == null || formerContextInstance.getTimestamp() < contextInstance.getTimestamp()) {
            LOGGER.info("Updating contextInstance {} to {}", contextInstance.getName(), contextInstance.getValue());
            contextMap.put(contextInstance.getName(), contextInstance);
            dispatchEvent(EventType.CONTEXT_UPDATED, contextInstance);

            if(contextsPublishedAsUpdated.contains(contextInstance.getName())) {
                publishContext(contextInstance.getName());
            }
        }
    }

    public void setPublishAsUpdated(String contextName) {
        LOGGER.info("Publish-as-updated set for context {}", contextName);
        contextsPublishedAsUpdated.add(contextName);
    }

    public void setPeriodicPublish(String contextName, Integer interval) {
        LOGGER.info("Periodic publish set for context {} every {} seconds", contextName, interval);
        periodicPublisher.scheduleAtFixedRate(()->publishContext(contextName, true), 0, interval, TimeUnit.SECONDS);
    }

    public ContextInstance getContext(String contextName) {
        return contextMap.get(contextName);
    }

    public List<ContextInstance> listContexts() {
        return new ArrayList<>(contextMap.values());
    }
}

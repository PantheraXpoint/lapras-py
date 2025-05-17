package kr.ac.kaist.cdsn.lapras.communicator;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import org.eclipse.paho.client.mqttv3.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;

/**
 * Created by Daekeun Lee on 2016-11-14.
 */
public class MqttCommunicator extends Component implements MqttCallback {
    private static Logger LOGGER = LoggerFactory.getLogger(MqttCommunicator.class);

    private MqttConnectOptions mqttConnectOptions = new MqttConnectOptions();
    private MqttClient mqttClient;

    private final String placeName;
    private final String brokerAddress;
    private final String clientId;

    private List<LaprasTopic> subscriptionList = new LinkedList<>();

    public MqttCommunicator(EventDispatcher eventDispatcher, Agent agent) throws MqttException {
        super(eventDispatcher, agent);

        this.placeName = agent.getAgentConfig().getPlaceName();
        this.brokerAddress = agent.getAgentConfig().getBrokerAddress();
        this.clientId = MqttClient.generateClientId();
        try {
            this.mqttClient = new MqttClient(this.brokerAddress, this.clientId, null);
            this.mqttClient.setCallback(this);
        } catch (MqttException e) {
            LOGGER.error("Cannot initiate MQTT client", e);
            throw e;
        }

        mqttConnectOptions.setCleanSession(true);
    }

    @Override
    public void setUp() {
        try {
            connect();
        } catch (MqttException e) {
        }
    }

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.SUBSCRIBE_TOPIC_REQUESTED);
        subscribeEvent(EventType.PUBLISH_MESSAGE_REQUESTED);
    }

    @Override
    protected boolean handleEvent(Event event) {
        try {
            if(!this.mqttClient.isConnected()) connect();
            switch(event.getType()) {
                case SUBSCRIBE_TOPIC_REQUESTED:
                    LaprasTopic topic = (LaprasTopic) event.getData();
                    topic.setPlaceName(placeName);
                    LOGGER.info("Subscribing to {}", topic);
                    subscriptionList.add(topic);
                    mqttClient.subscribe(topic.toString());
                    return true;
                case PUBLISH_MESSAGE_REQUESTED:
                    topic = (LaprasTopic) ((Object[])event.getData())[0];
                    MqttMessage message = (MqttMessage) ((Object[])event.getData())[1];
                    topic.setPlaceName(placeName);
                    LOGGER.info("Publishing to {}", topic);
                    mqttClient.publish(topic.toString(), message.getPayload(), message.getQos().value, message.getRetained());
                    return true;
            }
            return false;
        } catch (MqttException e) {
            return false;
        }
    }

    @Override
    public void messageArrived(String topic, org.eclipse.paho.client.mqttv3.MqttMessage message) throws Exception {
        LaprasTopic laprasTopic = new LaprasTopic(topic);
        dispatchEvent(EventType.MESSAGE_ARRIVED, new Object[]{laprasTopic, message.getPayload()});
    }

    public List<LaprasTopic> getSubscriptionList() {
        return new ArrayList<>(subscriptionList);
    }

    public void subscribeTopic(LaprasTopic topic) {
        dispatchEvent(EventType.SUBSCRIBE_TOPIC_REQUESTED, topic);
    }

    public void publish(LaprasTopic topic, MqttMessage message) {
        dispatchEvent(EventType.PUBLISH_MESSAGE_REQUESTED, new Object[]{ topic, message });
    }

    public void setWill(LaprasTopic topic, byte[] payload, int qos, boolean retained) {
        topic.setPlaceName(placeName);
        mqttConnectOptions.setWill(topic.toString(), payload, qos, retained);
    }

    synchronized private void connect() throws MqttException {
        try {
            LOGGER.debug("Connecting to MQTT broker at {}", this.brokerAddress);
            mqttClient.connect(mqttConnectOptions);
            for(LaprasTopic topic : subscriptionList)
                mqttClient.subscribe(topic.toString());
            LOGGER.info("Connected to MQTT broker");
        } catch (MqttException e) {
            LOGGER.error("Cannot connect to the MQTT broker: {}", this.brokerAddress);
            //e.printStackTrace();
            throw e;
        }
    }

    @Override
    public void connectionLost(Throwable cause) { }

    @Override
    public void deliveryComplete(IMqttDeliveryToken token) { }
}

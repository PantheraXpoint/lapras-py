package kr.ac.kaist.cdsn.lapras.user;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.communicator.LaprasTopic;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;
import kr.ac.kaist.cdsn.lapras.communicator.MqttCommunicator;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/**
 * Created by JWP on 2017. 9. 5..
 */
public class UserManager extends Component{
    private static final Logger LOGGER = LoggerFactory.getLogger(UserManager.class);
    private final MqttCommunicator mqttCommunicator;

    private final ConcurrentMap<String, Boolean> userPresenceMap = new ConcurrentHashMap<>();

    public UserManager(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);
        this.mqttCommunicator = agent.getMqttCommunicator();
    }

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.MESSAGE_ARRIVED);
        subscribeEvent(EventType.USER_NOTIFIED);
    }

    @Override
    public void setUp() {
        LaprasTopic topic = new LaprasTopic(null, MessageType.USER, LaprasTopic.SINGLELEVEL_WILDCARD);
        agent.getMqttCommunicator().subscribeTopic(topic);
    }

    @Override
    protected boolean handleEvent(Event event) {
        switch(event.getType()) {
            case MESSAGE_ARRIVED:
                LaprasTopic topic = (LaprasTopic) ((Object[]) event.getData())[0];
                if(topic.getMessageType() != MessageType.USER) return true;
                byte[] payload = (byte[]) ((Object[]) event.getData())[1];
                UserNotification userNotification = UserNotification.fromPayload(payload);
                if(userNotification != null) {
                    dispatchEvent(EventType.USER_NOTIFIED, userNotification);
                }
                break;
            case USER_NOTIFIED:
                UserNotification user = (UserNotification) event.getData();
                LOGGER.debug("User notified: {}", user.getName());
                break;
        }
        return true;
    }

    public void publishUserNotification(String userName, String publisher) {
        long timestamp = System.currentTimeMillis();

        Boolean userPresence = updateUserPresence(userName);

        UserNotification userNotification = new UserNotification(userName, userPresence, timestamp, publisher);
        LaprasTopic topic = new LaprasTopic(null, MessageType.USER, userName);
        mqttCommunicator.publish(topic, userNotification);
    }

    public ConcurrentMap<String, Boolean> getUserPresenceMap() {return userPresenceMap;}

    private Boolean updateUserPresence(String userName) {

        Boolean userPresence = userPresenceMap.get(userName);

        if (userPresence != null) {
            userPresence = !userPresence;
            userPresenceMap.put(userName, userPresence);
        } else {
            userPresenceMap.put(userName, true);
            userPresence = true;
        }

        LOGGER.debug(userPresenceMap.toString());

        return userPresence;
    }
}

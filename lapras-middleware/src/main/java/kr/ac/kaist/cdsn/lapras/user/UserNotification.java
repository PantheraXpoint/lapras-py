package kr.ac.kaist.cdsn.lapras.user;

import com.google.gson.JsonObject;
import kr.ac.kaist.cdsn.lapras.communicator.*;

/**
 * Created by JWP on 2017. 9. 5..
 */
public class UserNotification extends LaprasMessage {
    private Boolean presence;

    public UserNotification() {
    }

    public UserNotification(String name, Boolean presence, Long timestamp, String publisher) {
        super(name, timestamp, publisher);
        setPresence(presence);
    }

    public static UserNotification fromPayload(byte[] payload) {
        JsonObject jsonObject = MqttMessage.fromPayload(payload, UserNotification.class);
        if(jsonObject != null) {
            Boolean presence = jsonObject.get("presence").getAsBoolean();
            return new UserNotification(jsonObject.get("name").getAsString(),
                    presence,
                    jsonObject.get("timestamp").getAsLong(),
                    jsonObject.get("publisher").getAsString());
        } else return null;
    }

    public void setPresence(Boolean presence) {this.presence = presence;}

    public Boolean getPresence() {return this.presence;}

    @Override
    public MessageType getType() {
        return MessageType.USER;
    }

    @Override
    public MessageQos getQos() {
        return MessageQos.EXACTLY_ONCE;
    }

    @Override
    public boolean getRetained() {
        return false;
    }
}

package kr.ac.kaist.cdsn.lapras.communicator;

import com.google.gson.Gson;
import com.google.gson.JsonObject;

/**
 * Created by Daekeun Lee on 2016-12-05.
 */
public abstract class LaprasMessage implements MqttMessage {
    protected String name;
    protected String publisher;
    protected Long timestamp;

    public LaprasMessage() {}

    public LaprasMessage(String name, Long timestamp, String publisher) {
        this.name = name;
        this.timestamp = timestamp;
        this.publisher = publisher;
    }

    public static <T extends LaprasMessage> T fromPayload(byte[] payload, Class<T> clazz) {
        JsonObject jsonObject = MqttMessage.fromPayload(payload, clazz);
        return (new Gson()).fromJson(jsonObject, clazz);
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getPublisher() {
        return publisher;
    }

    public void setPublisher(String publisher) {
        this.publisher = publisher;
    }

    public Long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Long timestamp) {
        this.timestamp = timestamp;
    }
}

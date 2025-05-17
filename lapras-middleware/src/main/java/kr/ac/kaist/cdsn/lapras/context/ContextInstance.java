package kr.ac.kaist.cdsn.lapras.context;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import kr.ac.kaist.cdsn.lapras.communicator.LaprasMessage;
import kr.ac.kaist.cdsn.lapras.communicator.MessageQos;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;
import kr.ac.kaist.cdsn.lapras.communicator.MqttMessage;

/**
 * Created by Daekeun Lee on 2016-11-14.
 */
public class ContextInstance extends LaprasMessage {
    private Object value;
    private String valueType;

    public ContextInstance() {
    }

    public ContextInstance(String name, Object value, Long timestamp, String publisher) {
        super(name, timestamp, publisher);
        setValue(value);
    }

    public static ContextInstance fromPayload(byte[] payload) {
        JsonObject jsonObject = MqttMessage.fromPayload(payload, ContextInstance.class);
        if(jsonObject != null) {
            Object value;
            try {
                Gson gson = new Gson();
                value = gson.fromJson(jsonObject.get("value"), Class.forName(jsonObject.get("valueType").getAsString()));
            } catch (ClassNotFoundException e) {
                value = jsonObject.get("value").getAsString();
            }
            return new ContextInstance(jsonObject.get("name").getAsString(),
                    value,
                    jsonObject.get("timestamp").getAsLong(),
                    jsonObject.get("publisher").getAsString());
        } else return null;
    }

    public Object getValue() {
        return value;
    }

    public void setValue(Object value) {
        this.value = value;
        this.valueType = value.getClass().getTypeName();
    }

    public Class getValueType() {
        try {
            return Class.forName(valueType);
        } catch (ClassNotFoundException e) {
            return String.class;
        }
    }

    @Override
    public MessageType getType() {
        return MessageType.CONTEXT;
    }

    @Override
    public MessageQos getQos() {
        return MessageQos.AT_LEAST_ONCE;
    }

    @Override
    public boolean getRetained() {
        return true;
    }
}

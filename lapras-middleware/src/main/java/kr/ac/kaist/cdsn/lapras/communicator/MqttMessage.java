package kr.ac.kaist.cdsn.lapras.communicator;

import com.google.gson.*;

/**
 * Created by Daekeun Lee on 2016-11-14.
 */
public interface MqttMessage {
    MessageType getType();
    MessageQos getQos();
    boolean getRetained();

    default byte[] getPayload() {
        Gson gson = new Gson();
        return gson.toJson(this).getBytes();
    }

    static <T extends MqttMessage> JsonObject fromPayload(byte[] payload, Class<T> clazz) {
        JsonParser jsonParser = new JsonParser();
        try {
            return jsonParser.parse(new String(payload)).getAsJsonObject();
        } catch(JsonSyntaxException e) {
            return null;
        } catch(JsonParseException e) {
            return null;
        }
    }
}

package kr.ac.kaist.cdsn.lapras.communicator;

import java.util.Arrays;

/**
 * Created by Daekeun Lee on 2016-11-15.
 */
public class LaprasTopic extends MqttTopic {
    public LaprasTopic(String placeName, MessageType messageType, String... subtopics) {
        tokens = new String[2 + subtopics.length];
        setPlaceName(placeName);
        setMessageType(messageType);
        setSubtopics(subtopics);
    }

    public LaprasTopic(String topicString) {
        super(topicString);
    }

    public String getPlaceName() {
        return tokens[0];
    }

    public void setPlaceName(String placeName) {
        tokens[0] = placeName;
    }

    public MessageType getMessageType() {
        return MessageType.fromString(tokens[1]);
    }

    public void setMessageType(MessageType messageType) {
        tokens[1] = (messageType == null) ? null : messageType.toString();
    }

    public String[] getSubtopics() {
        return Arrays.copyOfRange(tokens, 2, tokens.length);
    }

    public void setSubtopics(String... subtopics) {
        System.arraycopy(subtopics, 0, tokens, 2, subtopics.length);
    }
}

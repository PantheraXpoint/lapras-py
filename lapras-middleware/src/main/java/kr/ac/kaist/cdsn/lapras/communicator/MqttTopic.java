package kr.ac.kaist.cdsn.lapras.communicator;

/**
 * Created by Daekeun Lee on 2016-11-15.
 */
public abstract class MqttTopic {
    public static String SINGLELEVEL_WILDCARD = "+";
    public static String MULTILEVEL_WILDCARD = "#";
    public static String DELIMITER = "/";

    protected String[] tokens;

    public MqttTopic(String topicString) {
        tokens = topicString.split("/");
    }

    protected MqttTopic() {
    }

    public String toString() {
        StringBuilder sb = new StringBuilder();
        for(int i = 0;i<tokens.length;i++) {
            String token = tokens[i];
            if(token != null) {
                sb.append(token);
            } else {
                sb.append(SINGLELEVEL_WILDCARD);
            }
            if(i + 1 < tokens.length) {
                sb.append(DELIMITER);
            }
        }
        return sb.toString();
    }
}

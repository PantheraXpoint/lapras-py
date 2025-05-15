package kr.ac.kaist.cdsn.lapras.communicator;

/**
 * Created by Daekeun Lee on 2016-11-14.
 */
public enum MessageType {
    CONTEXT("context"),
    FUNCTIONALITY("functionality"),
    ACTION("action"),
    TASK("task"),
    USER("user"),
    TASK_INITIATION("task_initiation"),
    TASK_TERMINATION("task_termination");

    String name;
    MessageType(String name) {
        this.name = name;
    }

    public String toString(){
        return name;
    }

    public static MessageType fromString(String value) {
        for(MessageType m : MessageType.values()) {
            if(m.toString().equals(value))
                return m;
        }
        throw new IllegalArgumentException("No such enum constant with specified value");
    }
}

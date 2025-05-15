package kr.ac.kaist.cdsn.lapras.task;

import kr.ac.kaist.cdsn.lapras.communicator.LaprasMessage;
import kr.ac.kaist.cdsn.lapras.communicator.MessageQos;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;

import java.util.List;

/**
 * Created by Daekeun Lee on 2017-02-15.
 */
public class TaskNotification extends LaprasMessage {
    private List<String> involvedAgents;

    public TaskNotification() {
    }

    public TaskNotification(String name, Long timestamp, String publisher, List<String> involvedAgents) {
        super(name, timestamp, publisher);
        this.involvedAgents = involvedAgents;
    }

    public List<String> getInvolvedAgents() {
        return involvedAgents;
    }

    public static TaskNotification fromPayload(byte[] payload) {
        return LaprasMessage.fromPayload(payload, TaskNotification.class);
    }

    @Override
    public MessageType getType() {
        return MessageType.TASK;
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

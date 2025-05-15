package kr.ac.kaist.cdsn.lapras.task;

import kr.ac.kaist.cdsn.lapras.communicator.LaprasMessage;
import kr.ac.kaist.cdsn.lapras.communicator.MessageQos;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;

import java.util.Collection;
import java.util.HashSet;
import java.util.Set;

/**
 * Created by JWP on 2018. 4. 4..
 */
public class TaskTermination extends LaprasMessage {
    private int taskId;

    public TaskTermination() {
    }

    public TaskTermination(String name, Long timestamp, String publisher, int taskId) {
        super(name, timestamp, publisher);
        this.taskId = taskId;
    }

    public int getTaskId() {
        return taskId;
    }

    public static TaskTermination fromPayload(byte[] payload) {
        return LaprasMessage.fromPayload(payload, TaskTermination.class);
    }

    @Override
    public MessageType getType() {
        return MessageType.TASK_TERMINATION;
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

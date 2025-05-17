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
public class TaskInitiation extends LaprasMessage {
    private int id;
    private Set<String> involvedAgents;
    private Set<String> involvedUsers;

    public TaskInitiation() {
    }

    public TaskInitiation(String name, Long timestamp, String publisher, Collection<String> involvedAgents, Collection<String> involvedUsers) {
        super(name, timestamp, publisher);
        this.involvedAgents = new HashSet<>(involvedAgents);
        this.involvedUsers = new HashSet<>(involvedUsers);
    }

    public int getId() {
        return id;
    }

    public Set<String> getInvolvedAgents() {
        return involvedAgents;
    }

    public Set<String> getInvolvedUsers() {
        return involvedUsers;
    }

    public static TaskInitiation fromPayload(byte[] payload) {
        return LaprasMessage.fromPayload(payload, TaskInitiation.class);
    }

    @Override
    public MessageType getType() {
        return MessageType.TASK_INITIATION;
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

package kr.ac.kaist.cdsn.lapras.action;

import kr.ac.kaist.cdsn.lapras.communicator.LaprasMessage;
import kr.ac.kaist.cdsn.lapras.communicator.MessageQos;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;

/**
 * Created by Daekeun Lee on 2016-11-24.
 */
public class ActionInstance extends LaprasMessage {
    private Object[] arguments;

    public ActionInstance() {
    }

    public ActionInstance(String name, Long timestamp, String publisher) {
        super(name, timestamp, publisher);
    }

    public ActionInstance(String name, Long timestamp, String publisher, Object[] arguments) {
        super(name, timestamp, publisher);
        this.arguments = arguments;
    }

    public static ActionInstance fromPayload(byte[] payload) {
        return LaprasMessage.fromPayload(payload, ActionInstance.class);
    }

    public Action getAction() {
        return new Action(name, arguments);
    }

    @Override
    public MessageType getType() {
        return MessageType.ACTION;
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

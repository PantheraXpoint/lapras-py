package kr.ac.kaist.cdsn.lapras.event;

/**
 * Created by Daekeun Lee on 2016-11-14.
 */
public interface EventConsumer {
    void receiveEvent(Event e);
}

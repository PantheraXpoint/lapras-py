package kr.ac.kaist.cdsn.lapras.event;

/**
 * Created by Daekeun Lee on 2016-11-11.
 */
public interface Event {
    EventType getType();
    Object getData();
}

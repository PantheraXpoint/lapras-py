package kr.ac.kaist.cdsn.lapras.communicator;

/**
 * Created by Daekeun Lee on 2016-11-14.
 */
public enum MessageQos {
    AT_MOST_ONCE(0),
    AT_LEAST_ONCE(1),
    EXACTLY_ONCE(2);

    int value;
    MessageQos(int value) {
        this.value = value;
    }
}

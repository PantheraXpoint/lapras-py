package kr.ac.kaist.cdsn.lapras;

/**
 * Created by Daekeun Lee on 2016-12-07.
 */
public class LaprasException extends Exception {
    public LaprasException(String message) {
        super(message);
    }

    public LaprasException(String message, Throwable cause) {
        super(message, cause);
    }
}

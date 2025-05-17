package kr.ac.kaist.cdsn.lapras.agents.airmonitor;

/**
 * Created by Jeongwook on 2017-05-01.
 *
 */
public class DataNotAvailableException extends Exception {
    public DataNotAvailableException(String message) {
        super(message);
    }

    public DataNotAvailableException(Throwable t) {
        super(t);
    }

    public DataNotAvailableException(String m, Throwable t) {
        super(m, t);
    }

}
package kr.ac.kaist.cdsn.lapras.agents.airmonitor;

/**
 * Created by Jeongwook on 2017-05-01.
 *
 */
public interface AirDataProvider extends AutoCloseable {
    AirData get() throws DataNotAvailableException;
}
package kr.ac.kaist.cdsn.lapras.agents.airmonitor;

/**
 * Created by Jeongwook on 2017-05-01.
 *
 */
public class AirData {
    /**
     * Concentration of particulate matter (µg/m³)
     */
    private final double particulateMatter;
    /**
     * Concentration of carbon dioxide (ppm)
     */
    private final double carbonDioxide;
    /**
     * Concentration of volatile compounds (ppb)
     */
    private final double volatileCompounds;
    /**
     * An air pollution rate (%)
     */
    private final double airPollution;

    AirData(double particulateMatter, double carbonDioxide,
            double volatileCompounds, double airPollution) throws IllegalArgumentException {
        if (particulateMatter < 0.0 || carbonDioxide < 0.0 || volatileCompounds < 0.0 ||
                airPollution < 0.0) {
            throw new IllegalArgumentException("any of fields cannot have negative value");
        }
        if (airPollution > 100.0) {
            throw new IllegalArgumentException("air pollution field cannot have a value " +
                    "greater than 100.0");
        }
        this.particulateMatter = particulateMatter;
        this.carbonDioxide = carbonDioxide;
        this.volatileCompounds = volatileCompounds;
        this.airPollution = airPollution;
    }

    AirData(final AirData d) {
        this.particulateMatter = d.particulateMatter;
        this.carbonDioxide = d.carbonDioxide;
        this.volatileCompounds = d.volatileCompounds;
        this.airPollution = d.airPollution;
    }

    public double getParticulateMatter() {
        return particulateMatter;
    }

    public double getCarbonDioxide() {
        return carbonDioxide;
    }

    public double getVolatileCompounds() {
        return volatileCompounds;
    }

    public double getAirPollution() {
        return airPollution;
    }
}
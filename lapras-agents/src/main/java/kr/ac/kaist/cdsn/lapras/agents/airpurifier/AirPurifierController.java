package kr.ac.kaist.cdsn.lapras.agents.airpurifier;

import com.phidgets.PhidgetException;
import kr.ac.kaist.cdsn.lapras.agents.phidget.PhidgetIRController;

public class AirPurifierController extends PhidgetIRController {
	public AirPurifierController(int phidgetSerial) throws PhidgetException {
        super(phidgetSerial);
	}

	public boolean speedDown() {
		return transmit(SPEED_DOWN);
	}

	public boolean speedUp() {
		return transmit(SPEED_UP);
	}

	public boolean turnOn() {
		return transmit(TURN_ON);
	}

	public boolean turnOff() {
		return transmit(TURN_OFF);
	}

	private final static int[] SPEED_UP = {
			9030,   4540,    570,    550,    580,   1670,    590,    540,    570,    560,
			570,   1680,    580,    540,    570,    560,    520,    600,    530,   1720,
			580,    550,    570,   1680,    580,   1670,    580,    540,    530,   1720,
			580,   1670,    580,   1670,    580,   1670,    580,    550,    520,    600,
			530,    600,    530,   1720,    520,    610,    520,    600,    530,    600,
			520,    600,    530,   1720,    530,   1720,    530,   1720,    580,    550,
			520,   1730,    530,   1720,    520,   1730,    530
	};

	private final static int[] SPEED_DOWN = {
			9040,   4530,    580,    540,    580,   1670,    580,    550,    580,    540,
			580,   1670,    580,    550,    580,    540,    580,    550,    570,   1680,
			580,    540,    580,   1670,    580,   1670,    580,    550,    570,   1680,
			580,   1670,    570,   1680,    580,    540,    580,    550,    520,    600,
			530,    600,    520,   1730,    520,    600,    530,    600,    520,    600,
			530,   1720,    530,   1720,    580,   1670,    580,   1670,    580,    550,
			520,   1730,    530,   1720,    570,   1680,    580
	};

	private final static int[] TURN_ON = {
			9010,      4560,       490,       660,       470,      1810,       440,       630,       490,       640,
			490,      1760,       500,       630,       480,       690,       440,       640,       490,      1760,
			490,       630,       490,      1760,       490,      1810,       450,       660,       460,      1760,
			490,      1760,       540,      1710,       510,      1740,       490,      1760,       520,       600,
			490,       640,       490,      1760,       490,       660,       470,       630,       490,       690,
			430,       670,       460,       640,       490,      1780,       470,      1810,       440,       630,
			490,      1760,       520,      1730,       490,      1730,       570,     40250,      9030,      2290,
			520
	};

	private final static int[] TURN_OFF = {
			9030,      4560,       490,       640,       480,      1760,       500,       660,       470,       650,
			460,      1790,       470,       630,       500,       650,       470,       660,       470,      1780,
			460,       670,       460,      1760,       500,      1780,       460,       660,       470,      1780,
			470,      1760,       480,      1770,       490,      1780,       470,      1810,       440,       660,
			470,       660,       460,      1790,       480,       640,       460,       670,       460,       660,
			470,       630,       500,       630,       490,      1790,       460,      1790,       460,       640,
			490,      1780,       460,      1770,       490,      1780,       460,     40310,      9030,      2310,
			500

	};
}

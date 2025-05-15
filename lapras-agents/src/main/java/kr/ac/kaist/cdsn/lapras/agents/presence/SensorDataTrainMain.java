package kr.ac.kaist.cdsn.lapras.agents.presence;

import kr.ac.kaist.cdsn.lapras.util.log.Logger;
import kr.ac.kaist.cdsn.lapras.util.log.LoggerPrintMode;

/**
 * Created by chad1231 on 12/01/2017.
 */
public class SensorDataTrainMain {
	public static void main(String[] args){
		Logger.setMode(new LoggerPrintMode[] {LoggerPrintMode.INFO});
		Thread trainT = new Thread(new SensorDataTrainThread(
				Constants.N1Lounge8F_Name,
				Constants.TOTAL_TRAIN_DURATION,
				Constants.DATA_PROCECCING_INTERVAL_UNIT,
				Constants.TRAIN_LABEL));
		trainT.run();
	}
}

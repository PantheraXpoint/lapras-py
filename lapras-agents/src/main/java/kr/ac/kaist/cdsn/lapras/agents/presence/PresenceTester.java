package kr.ac.kaist.cdsn.lapras.agents.presence;

import kr.ac.kaist.cdsn.lapras.learning.model.KNN;
import kr.ac.kaist.cdsn.lapras.util.log.Logger;
import kr.ac.kaist.cdsn.lapras.util.log.LoggerPrintMode;

/**
 * Created by chad1231 on 12/01/2017.
 */
public class PresenceTester {
	public static void main(String[] args){
		Logger.setMode(new LoggerPrintMode[]{LoggerPrintMode.INFO});
		String fName = "lapras-agents/src/main/resources/n1_825_presence_train_data.arff";
		String[] query1 = {"7","2","524"}; //present
		String[] query2 = {"2","1","5746"}; //present
		String[] query3 = {"0","0","104502"}; //empty

		String answer = KNN.getInstance(15, fName).getClassID(query3);
		Logger.info("Answer = "+answer);
	}
}

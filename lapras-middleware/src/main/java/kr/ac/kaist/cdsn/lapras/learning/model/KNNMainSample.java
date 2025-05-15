package kr.ac.kaist.cdsn.lapras.learning.model;

import kr.ac.kaist.cdsn.lapras.util.log.Logger;
import kr.ac.kaist.cdsn.lapras.util.log.LoggerPrintMode;

/**
 * Created by chad1231 on 11/01/2017.
 */
public class KNNMainSample {
	public static void main(String[] args){
		Logger.setMode(new LoggerPrintMode[]{LoggerPrintMode.INFO, LoggerPrintMode.DEBUG});
		String fName = "lapras-agents/src/main/java/kr/ac/kaist/cdsn/lapras/agents/util/model/sample_data.arff";
		String[] query1 = {"22","3","3.4"}; //present, 14:1
		String[] query2 = {"4","1","0.5"}; //present, 9:6
		String[] query3 = {"0","1","30"}; //empty, 9:6

		String[] query4 = {null,"3","3.4"}; // present, 13:2
		String[] query5 = {"4",null,"0.5"}; // present, 9:6
		String[] query6 = {"0","1",null}; //empty, 11:4

		String answer = KNN.getInstance(15, fName).getClassID(query5);
		Logger.info("Answer = "+answer);
	}
}

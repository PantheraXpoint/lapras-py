package kr.ac.kaist.cdsn.lapras.learning.data;

/**
 * Created by chad1231 on 12/01/2017.
 */
public class ArffFileGenMain {
	public static void main(String[] args){
		String inputFile = "lapras-agents/src/main/java/kr/ac/kaist/cdsn/lapras/agents/util/model/sample_data.arff";
		String outputFile = "lapras-agents/src/main/java/kr/ac/kaist/cdsn/lapras/agents/util/model/sample_train_data.arff";

		ArffFileGen.genArffFile(ArffParser.getInstance(inputFile).getDataset(), outputFile);
	}
}

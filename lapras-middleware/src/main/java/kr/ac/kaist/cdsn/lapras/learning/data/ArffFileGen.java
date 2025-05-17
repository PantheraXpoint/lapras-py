package kr.ac.kaist.cdsn.lapras.learning.data;

import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;

/**
 * Created by chad1231 on 12/01/2017.
 */
public class ArffFileGen {
	private static ArffFileGen _instance;

	public static void genArffFile(ArffDataset dataset, String outPath){
		if(_instance == null) _instance = new ArffFileGen();

		Charset utf8 = StandardCharsets.UTF_8;
		List<String> lines = new ArrayList<String>();

		boolean fileExists = Files.exists(Paths.get(outPath));

		if(!fileExists){
			lines.add("@RELATION "+dataset.getRelation()+"\n");

			for(ArffAttribute attr : dataset.getAttrList()){
				lines.add("@ATTRIBUTE "+attr.getName()+" "+attr.getType().toString());
			}


			String classStr = "@ATTRIBUTE class {";
			for(int i=0; i<dataset.getClassList().size(); i++){
				classStr += (dataset.getClassList().get(i)+",");
			}
			classStr = classStr.substring(0, classStr.length()-1);
			classStr += "}";
			lines.add(classStr);

			lines.add("");

			if(dataset.getAttrWeight()!=null){
				String weightStr = "";
				for(int i=0; i<dataset.getAttrWeight().size(); i++){
					weightStr += (dataset.getAttrWeight().get(i).doubleValue()+",");
				}
				lines.add("@WEIGHT "+weightStr.substring(0, weightStr.length()-1));
			}

			lines.add("");

			lines.add("@DATA");
		}

		for(ArffDataInstance data : dataset.getDataset()){
			lines.add(data.toNaiveString());
		}

		try {
			if(!fileExists){
				Files.write(Paths.get(outPath), lines, utf8, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
			}else{
				Files.write(Paths.get(outPath), lines, utf8, StandardOpenOption.APPEND);
			}
		} catch (IOException e) {
			e.printStackTrace();
		}
	}
}

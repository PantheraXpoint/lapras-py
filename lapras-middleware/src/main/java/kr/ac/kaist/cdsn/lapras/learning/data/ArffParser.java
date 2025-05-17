package kr.ac.kaist.cdsn.lapras.learning.data;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

/**
 * Created by chad1231 on 11/01/2017.
 */
public class ArffParser {
	private static ArffParser _instance;

	private String fName;
	private ArffDataset dataset;
	private boolean dStarted;

	private ArffParser(String fName) {
		this.fName = fName;
		dStarted = false;
		loadData();
	}

	public static ArffParser getInstance(String fName) {
		if (_instance == null) {
			_instance = new ArffParser(fName);
		}

		return _instance;
	}

	private void loadData() {
		dataset = new ArffDataset();

		BufferedReader br = null;
		FileReader fr = null;

		try {
			fr = new FileReader(fName);
			br = new BufferedReader(fr);

			String sCurrentLine;

			br = new BufferedReader(new FileReader(fName));

			while ((sCurrentLine = br.readLine()) != null) {
				if(sCurrentLine.startsWith("@RELATION")){
					dataset.setRelation(sCurrentLine.split("\\s")[1]);
				}else if(sCurrentLine.startsWith("@ATTRIBUTE")){
					String[] attrArr = sCurrentLine.split("\\s");
					ArffAttribute.AttrType attrType = null;

					if(attrArr[1].trim().equals("class")){
						String[] classArr = attrArr[2].split(",");
						for(String c : classArr){
							if(c.contains("}")){
								c = c.substring(0, c.length()-1);
							}

							if(c.contains("{")){
								c = c.substring(1);
							}

							dataset.addClass(c);
						}
					}else{
						attrType = (attrArr[2].toLowerCase().equals("numeric")?ArffAttribute.AttrType.NUMERIC:ArffAttribute.AttrType.STRING);
						dataset.addAttribute(new ArffAttribute(attrArr[1].trim(), attrType));
					}
				}else if(sCurrentLine.startsWith("@WEIGHT")){
					String[] weightLineArr = sCurrentLine.split("\\s");
					String[] weightArr = weightLineArr[1].split(",");
					dataset.setAttrWeight(weightArr);
				}else if(sCurrentLine.startsWith("@DATA")){
					this.dStarted = true;
				}else{
					if(this.dStarted == true && !sCurrentLine.equals("")){
						dataset.addDataInstance(new ArffDataInstance(dataset, sCurrentLine));
					}
				}
			}
		} catch (IOException e) {
			e.printStackTrace();
		} finally {
			try {
				if (br != null)	br.close();
				if (fr != null)	fr.close();
			} catch (IOException ex) {
				ex.printStackTrace();
			}
		}
	}

	public void printDataset(){
		for(int i=0; i<this.dataset.getSize(); i++){
			System.out.println(this.dataset.getData(i).toString());
		}
	}

	public ArffDataset getDataset(){
		return this.dataset;
	}
}

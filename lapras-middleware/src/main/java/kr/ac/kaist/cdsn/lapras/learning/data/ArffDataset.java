package kr.ac.kaist.cdsn.lapras.learning.data;

import java.util.ArrayList;

/**
 * Created by chad1231 on 11/01/2017.
 */
public class ArffDataset {
	private String relation;
	private ArrayList<ArffAttribute> attrList;
	private ArrayList<ArffDataInstance> dataset;
	private ArrayList<String> classList;
	private ArrayList<Double> attrWeight;

	public ArffDataset(){
		attrList = new ArrayList<ArffAttribute>();
		dataset = new ArrayList<ArffDataInstance>();
		classList = new ArrayList<String>();
		attrWeight = null;
	}

	public void setRelation(String relation){
		this.relation = relation;
	}
	public String getRelation(){ return this.relation;}

	public void setAttrWeight(String[] weight){
		attrWeight = new ArrayList<Double>();
		for(String w : weight){
			this.attrWeight.add(Double.parseDouble(w));
		}
	}

	public void setAttrWeight(ArrayList<Double> weight){
		for(Double w : weight){
			this.attrWeight.add(w);
		}
	}

	public void setAttrList(ArrayList<ArffAttribute> attributes){
		for(ArffAttribute attr : attributes){
			this.attrList.add(attr);
		}
	}

	public void addAttribute(ArffAttribute attr){
		attrList.add(attr);
	}

	public void addDataInstance(ArffDataInstance instance){
		dataset.add(instance);
	}

	public void addClass(String c){
		classList.add(c);
	}

	public ArrayList<ArffAttribute> getAttrList(){
		return this.attrList;
	}

	public ArffDataInstance getData(int i){
		return this.dataset.get(i);
	}
	public ArrayList<ArffDataInstance> getDataset(){return this.dataset;}

	public ArffAttribute.AttrType[] getAttrTypeList(){
		ArffAttribute.AttrType[] attrTypeList = new ArffAttribute.AttrType[this.attrList.size()];

		for(int i=0; i<this.attrList.size();i++){
			attrTypeList[i] = this.attrList.get(i).getType();
		}

		return attrTypeList;
	}

	public int getSize(){
		return this.dataset.size();
	}

	public ArrayList<String> getClassList(){
		return this.classList;
	}

	public void setClassList(String[] cList){
		for(String c : cList){
			this.classList.add(c);
		}
	}

	public ArrayList<Double> getAttrWeight(){
		return this.attrWeight;
	}
}

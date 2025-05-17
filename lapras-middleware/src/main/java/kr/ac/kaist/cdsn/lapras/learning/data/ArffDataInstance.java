package kr.ac.kaist.cdsn.lapras.learning.data;

import java.util.ArrayList;
import java.util.Arrays;

/**
 * Created by chad1231 on 11/01/2017.
 */
public class ArffDataInstance {
	private ArffAttribute.AttrType[] typeDef;
	private String[] values;
	private String dClass;

	public ArffDataInstance(ArffDataset dataset){
		this.typeDef = new ArffAttribute.AttrType[dataset.getAttrList().size()];
		this.values = new String[this.typeDef.length];

		for(int i=0; i<this.typeDef.length; i++){
			this.typeDef[i] = dataset.getAttrList().get(i).getType();
		}
	}

	public ArffDataInstance(ArffDataset dataset, String dLine){
		this(dataset);

		String[] dArr = dLine.split(",");
		for(int i=0; i<values.length; i++){
			this.values[i] = dArr[i];
		}
		this.dClass = dArr[this.values.length];
	}

	public ArffDataInstance(ArffAttribute.AttrType[] type, String[] values, String dClass){
		this.typeDef = new ArffAttribute.AttrType[type.length];
		this.values = new String[values.length];
		this.dClass = dClass;

		for(int i=0; i<type.length; i++){
			this.typeDef[i] = type[i];
		}

		for(int i=0; i<values.length; i++){
			this.values[i] = values[i];
		}
	}

	public ArffDataInstance(String[] values){
		this.values = new String[values.length];
		for(int i=0; i<values.length; i++){
			this.values[i] = values[i];
		}
	}

	public void setValues(String[] values){
		this.values = new String[values.length];
		for(int i=0; i<values.length; i++){
			this.values[i] = values[i];
		}
	}

	public void setClass(String clazz){
		this.dClass = clazz;
	}

	public String get(int i){
		return this.values[i];
	}

	public String getDClass(){
		return this.dClass;
	}

	public String toString(){
		return ("{values : "+ Arrays.toString(values)+", class : "+this.dClass+"}");
	}
	public String toNaiveString(){
		String nStr = "";
		for(String value : values){
			nStr += (value+",");
		}
		nStr += dClass;

		return nStr;
	}
	public String[] getValues(){
		return this.values;
	}
}

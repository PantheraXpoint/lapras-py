package kr.ac.kaist.cdsn.lapras.learning.data;

/**
 * Created by chad1231 on 11/01/2017.
 */
public class ArffAttribute {
	private String name;
	private AttrType type;

	public ArffAttribute(String name, AttrType type){
		this.name = name;
		this.type = type;
	}

	public static enum AttrType{
		NUMERIC{
			public String toString(){
				return "NUMERIC";
			}
		}, STRING{
			public String toString(){
				return "STRING";
			}
		};
	}

	public String getName(){
		return this.name;
	}

	public AttrType getType(){
		return this.type;
	}
}

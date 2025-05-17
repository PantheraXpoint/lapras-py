package kr.ac.kaist.cdsn.lapras.agents.ambient.xbee;

public class SensorInfo {

	private String name;
	private double temperature;
	private double light;
	private double humidity;
	private String time;
	
	
	public SensorInfo(String name){
		this.name = name;
	}
	
	public String getName(){
		return this.name;
	}
	
	public double getTemperature(){
		return temperature;
	}
	
	public double getLight(){
		return light;
	}
	
	public String getTime(){
		return time;
	}
	
	public void setTime(String time){
		this.time = time;
	}
	
	public double getHumidity(){
		return humidity;
	}
	
	public void setLight(double l){
		this.light = l;
	}
	
	
	public void setTemperature(double t){
		this.temperature = t;
	}
	

	
	public void setHumidity(double h){
		this.humidity = h;
	}
	
	public String toString(){
		String c = "Sensor : "+ this.getName()+"\n";
		c+="Temperature : "+ this.getTemperature()+ "\n";
		c+="Humidity : " + this.getHumidity() + "\n";
		c+="Light : " + this.getLight() + "\n";
		c+="Time : " + this.getTime() + "\n";
		return c;
	}
}
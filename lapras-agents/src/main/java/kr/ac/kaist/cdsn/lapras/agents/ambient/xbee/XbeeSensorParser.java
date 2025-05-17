package kr.ac.kaist.cdsn.lapras.agents.ambient.xbee;


import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;


public class XbeeSensorParser {
	
	private final String USER_AGENT = "Mozilla/5.0";
	private final String url ;
	private String response_msg;
	private JSONParser j;
    private ArrayList<SensorInfo> sensorinfo_list;
    
    
    public XbeeSensorParser(String url){
    	
    	this.url = url;
    }
	
	private void sendGet() throws Exception {
		 
		
 
		URL obj = new URL(url);
		HttpURLConnection con = (HttpURLConnection) obj.openConnection();
 
		// optional default is GET
		con.setRequestMethod("GET");
 
		//add request header
		con.setRequestProperty("User-Agent", USER_AGENT);
 
		int responseCode = con.getResponseCode();
		System.out.println("\nSending 'GET' request to URL : " + url);
		System.out.println("Response Code : " + responseCode);
 
		BufferedReader in = new BufferedReader(
		        new InputStreamReader(con.getInputStream()));
		String inputLine;
		StringBuffer response = new StringBuffer();
 
		while ((inputLine = in.readLine()) != null) {
			response.append(inputLine);
		}
		in.close();
 
		//print result
	   response_msg=response.toString();
 
	}

	public void getSensorValue(){
		try{
			sendGet();

			j = new JSONParser(response_msg);
			//j.printParsedSensorData();
			sensorinfo_list = j.getParsedList();
		
		}
		catch (Exception e){
			e.printStackTrace();
		}
	}
	
	public ArrayList<String> getAvailableDeviceNames(){
		ArrayList<String> a = new ArrayList<String>();
		if (sensorinfo_list != null){
			for (int i=0;i<sensorinfo_list.size();i++){
				a.add(sensorinfo_list.get(i).getName());
			}
			
		}else{
			System.out.println("sensorinfo is null");
		}
		return a;
	}
	
	public SensorInfo getSensorByName(String name){
		SensorInfo s = null ;
		
		if (sensorinfo_list!=null){
			for (int i=0;i<sensorinfo_list.size();i++){
				s = sensorinfo_list.get(i);
				if(name.equals(s.getName())){
					break;
				}
			} 
			
		}else{
			System.out.println("sensorinfo is null");
		}
		return s;
	}
	
	/*
	public double getTemperature(String sensorname){
		double t = -1;
		SensorInfo s = getSensorByName(sensorname);
		if (s!=null){
			t = s.getTemperature();
		}
		return t;
	}
	
	public double getHumidity(String sensorname){
		double h = -1;
		SensorInfo s = getSensorByName(sensorname);
		if (s!=null){
			h = s.getHumidity();
		}
		return h;
	}
	
	public double getLight(String sensorname){
		double l = -1;
		SensorInfo s = getSensorByName(sensorname);
		if (s!=null){
			l = s.getLight();
		}
		return l;
	}
	
	public String getTime(String sensorname){
		String time = "";
		SensorInfo s = getSensorByName(sensorname);
		if (s!=null){
			time = s.getTime();
		}
		return time;
	}*/
	
}

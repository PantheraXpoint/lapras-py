package kr.ac.kaist.cdsn.lapras.agents.ambient.xbee;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.util.ArrayList;

public class JSONParser {

	private static final String TAG_DEVICELIST = "devices";
	private static final String TAG_CHANNELS = "channels";
	private static final String TAG_NAME = "name";
	private static final String TAG_TIME = "time";
	private static final String TAG_VALUE = "value";

	private ArrayList<SensorInfo> sensorinfo_list;

	public JSONParser(String json) {
		parseJSON(json);
	}

	private void parseJSON(String json) {
		JsonObject jObj;
		try {
			JsonParser p = new JsonParser();
			jObj = (JsonObject) p.parse(json);
			sensorinfo_list = new ArrayList<SensorInfo>();

			JsonArray device_list = jObj.get(TAG_DEVICELIST).getAsJsonArray();

			// looping through All Contacts
			for (int i = 0; i < device_list.size(); i++) {
				JsonObject f = device_list.get(i).getAsJsonObject();

				String name = f.get(TAG_NAME).getAsString();
				SensorInfo si = new SensorInfo(name);

				JsonArray sensorvalues = f.get(TAG_CHANNELS).getAsJsonArray();
				for (int k = 0; k < sensorvalues.size(); k++) {

					JsonObject sv = sensorvalues.get(k).getAsJsonObject();
					// Storing each json item in variable
					String valuename = sv.get(TAG_NAME).getAsString();
					if (valuename.equals("temperature")) {
						double value = sv.get(TAG_VALUE).getAsDouble();
						si.setTemperature(value);
					} else if (valuename.equals("humidity")) {
						double value = sv.get(TAG_VALUE).getAsDouble();
						si.setHumidity(value);
					} else if (valuename.equals("light")) {
						double value = sv.get(TAG_VALUE).getAsDouble();
						si.setLight(value);
						String time = sv.get(TAG_TIME).getAsString();
						si.setTime(time);
					}

				}
				sensorinfo_list.add(si);
			}

		} catch (Exception e) {
			System.out.println("Error parsing data " + e.toString());
		}
	}

	public ArrayList<SensorInfo> getParsedList() {
		return sensorinfo_list;
	}

	public void printParsedSensorData() {
		for (int i = 0; i < sensorinfo_list.size(); i++) {
			SensorInfo o = sensorinfo_list.get(i);
			System.out.println("\n\n");
			System.out.println(o);
		}
	}
}


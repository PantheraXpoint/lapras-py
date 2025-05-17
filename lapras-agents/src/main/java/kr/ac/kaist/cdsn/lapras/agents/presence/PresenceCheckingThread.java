package kr.ac.kaist.cdsn.lapras.agents.presence;

//Imported for receiving sensing data (from API)

import m2m.model.device.Device;
import m2m.model.device.Gateway;
import m2m.model.device.LC;
import m2m.model.device.Sensor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Date;
import java.util.List;

/**
 * PresenceCheckingThread periodically checks whether a presence sensor detects a user movement.
 * If a movement is detected, PresenceCheckingThread updates a user presence status
 * for the place which is mapped to the detected place.
 *
 * @author Ryu Chungkwon (iDBLab KAIST)
 * @since 2015-11-12
 */
public class PresenceCheckingThread extends Thread {
	private static final Logger logger = LoggerFactory.getLogger(PresenceCheckingThread.class);
	private static PresenceDataServer dataServer;
	private boolean isRunning = false;
	private List<Gateway> gatewayList;

	public PresenceCheckingThread(PresenceDataServer ds, List<Gateway> gwList) {
		dataServer = ds;
		gatewayList = gwList;
	}

	public void run() {
		isRunning = true;

		for (Gateway gateway : gatewayList) {
			List<LC> lcList = gateway.getLcList();
			for (LC lc : lcList) {
				List<Device> deviceList = lc.getDeviceList();
				while (true) {
					for (Device device : deviceList) {
						if (device instanceof Sensor) {
							Sensor sensor = (Sensor) device;
							Date eventTime = sensor.getEventTime();

							//sensorID is hexadecimal(16-ary digit) number(e.g. 0x0C01 = 256*12 + 1 = 3073)
							short sensorID = sensor.getDeviceId();
							long eventTimeInMilis = 0L;
							if (eventTime != null) {
								eventTimeInMilis = eventTime.getTime();
							}

							switch (sensorID) {
								case 3073:
									dataServer.setUserPresence(Constants.N1_LOUNGE_8F, eventTimeInMilis);
									break;
								case 3074:
								case 3075:
								case 3076:
									dataServer.setUserPresence(Constants.N1_CORRIDOR_822, eventTimeInMilis);
									break;
								case 3077:
									dataServer.setUserPresence(Constants.N1_IDBLAB_822, eventTimeInMilis);
									break;
								case 3078:
								case 3079:
									dataServer.setUserPresence(Constants.N1_CDSNLAB_823, eventTimeInMilis);
									break;
								case 3080:
									dataServer.setUserPresence(Constants.N1_CNLAB_824, eventTimeInMilis);
									break;
								case 1386: //if seminar room sensor is changed, then check this
									dataServer.setUserPresence(Constants.N1_SEMINAR_825, eventTimeInMilis);
									break;
								default:
									break;
							}
						}
					}
					try {
						//Thread.sleep(1000);
						Thread.sleep(500);
					} catch (InterruptedException e) {
						e.printStackTrace();
					}
				}
			}
		}
	}

	public void terminate() {
		isRunning = false;
	}
}
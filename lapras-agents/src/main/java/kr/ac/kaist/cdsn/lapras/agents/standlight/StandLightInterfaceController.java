package kr.ac.kaist.cdsn.lapras.agents.standlight;

import com.phidgets.InterfaceKitPhidget;
import com.phidgets.PhidgetException;
import com.phidgets.event.*;
import kr.ac.kaist.cdsn.lapras.context.ContextManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;

/**
 * Created by chad1231 on 11/04/2018.
 *
 * This class is created to handle a slider and a light sensor
 * attached to a Phidget Interfacekit. The slider is installed
 * to ease a stand light control and the light sensor is installed
 * to keep track of physical status of the stand light. (FYI, the
 * physical status was supposed to be monitored by a power monitor,
 * but this phidget sensor is enough for that purpose.)
 *
 * @author chadson (heesuk.chad.son@gmail.com)
 * @date 11/04/2018
 */
public class StandLightInterfaceController {
	private static final Logger LOGGER = LoggerFactory.getLogger(StandLightInterfaceController.class);
	private StandLightIRController controller;
	private InterfaceKitPhidget interfaceKit = null;
	private InterfaceDataListener sensorListener;
	private StandLightAgent agent;
	private ContextManager ctxManager;

	private ArrayList<Integer> sliderValues;
	private ArrayList<Integer> lightValues;

	private Thread sensorMonitorT;

	public StandLightInterfaceController(int phidgetSerial,
										 StandLightIRController controller,
										 StandLightAgent agent, ContextManager ctxManager) {
		this.sliderValues = new ArrayList<Integer>();
		this.lightValues = new ArrayList<Integer>();

		this.controller = controller;
		this.agent = agent;

		this.initPhidget(phidgetSerial);
		this.sensorListener = new InterfaceDataListener(this);
		this.interfaceKit.addSensorChangeListener(sensorListener);
		this.ctxManager = ctxManager;

		this.sensorMonitorT = new Thread(new SensorQueueMonitor(this));
		this.sensorMonitorT.start();
		LOGGER.info("[StandLightInterfaceController] sensorMonitorT started.");
	}

	private void initPhidget(int serialNo){
		try {
			interfaceKit = new InterfaceKitPhidget();

			// opens interface kit using the serial number.
			// if the serial number is invalid, just open anything attached.
			if (serialNo > 0)
				interfaceKit.open(serialNo);
			else
				interfaceKit.openAny();

			LOGGER.info(" [PhidgetSensor] waiting for InterfaceKit attachment...");
			interfaceKit.waitForAttachment(2000);
			LOGGER.info("   -attached: " + interfaceKit.getDeviceID() +
					" (s/n: " + interfaceKit.getSerialNumber() + ")");

			interfaceKit.addAttachListener(new AttachListener() {
				public void attached(AttachEvent ae) {
					LOGGER.info("attachment of {}", ae);
				}
			});
			interfaceKit.addDetachListener(new DetachListener() {
				public void detached(DetachEvent ae) {
					LOGGER.info("detachment of ",ae);
				}
			});
			interfaceKit.addErrorListener(new ErrorListener() {
				public void error(ErrorEvent ee) {
					LOGGER.info("error event for ",ee);
				}
			});
			interfaceKit.addInputChangeListener(new InputChangeListener() {
				public void inputChanged(InputChangeEvent oe) {
					LOGGER.info("{}",oe);
				}
			});
			interfaceKit.addOutputChangeListener(new OutputChangeListener() {
				// called when output state changes
				public void outputChanged(OutputChangeEvent e) {
					// Redirect
					LOGGER.error("{}",e);
				}
			});
		} catch (PhidgetException e) {
			LOGGER.error(
					"  [PhidgetSensor] ERROR opening interface kit! Please check the serial number. " +
							"(input serialNo = {})", serialNo);
			e.printStackTrace();
		}
	}

	private class InterfaceDataListener implements SensorChangeListener {
		StandLightInterfaceController controller;

		public InterfaceDataListener(StandLightInterfaceController controller){
			super();
			this.controller = controller;
		}

		@Override
		public synchronized void sensorChanged(SensorChangeEvent event) {
			int value = event.getValue();
			switch (event.getIndex()) {
				case 0: // slider 60 - PN 1112
					LOGGER.debug("[StandLightInterfaceController] Changed event " +
							"value for slide = {}", value);
					this.controller.addSliderValue(value);
					break;
				case 1: // light - PN 1127
					LOGGER.debug("[StandLightInterfaceController] Changed event " +
							"value for light = {}", value);
					this.controller.addLightValue(value);
					break;
				default: // error
					LOGGER.debug("[StandLightInterfaceController] A wrong index " +
							"return is detected.");
					break;
			}
		}
	}

	/**
	 * Some sensor values are updated realtime, but MQTT is not a time-critical framework.
	 * For example, a slider sensor value may change more than 10 times per 0.5 second, but
	 * MQTT cannot support those fast publish actions. Therefore, it's safer to run an
	 * extra thread to selects the final sensor value after a sequence of changes in every
	 * second and pass the value to MQTT service. This SensorQueueMonitor Runnable is
	 * designed for that purpose.
	 */
	private class SensorQueueMonitor implements Runnable {
		int lastSliderValue;
		int lastLightValue;
		private StandLightInterfaceController controller;
		private StandLightAgent agent;

		final int CHECK_INTERVAL = 3000;

		public SensorQueueMonitor(StandLightInterfaceController controller){
			super();
			this.controller = controller;
			this.agent = this.controller.getAgent();
		}

		@Override
		public void run() {
			LOGGER.info("[SensorQueueMonitor] Monitoring thread started..");
			while(true){
				try {
					Thread.sleep(CHECK_INTERVAL);

					// (1) check the last value from the value queues
					// (2) apply and pass the value to MQTT
					// (2)-1. handle the slider value
					lastSliderValue = this.controller.getLastSliderValue();

					if(lastSliderValue < 50){
						this.agent.changeTo(0);
					}else if(lastSliderValue < 250){
						this.agent.changeTo(1);
					}else if(lastSliderValue < 500){
						this.agent.changeTo(2);
					} else if (lastSliderValue < 750) {
						this.agent.changeTo(3);
					}else{
						this.agent.changeTo(4);
					}
					LOGGER.debug("slider value is successfully applied.");
					Thread.sleep(500);

					// (2)-2. handle the light value
					lastLightValue = this.controller.getLastLightValue();
					LOGGER.debug("lastLightValue = {}",lastLightValue);

					if(lastLightValue < 10){
						this.agent.setLightOn(false);
					}else{
						this.agent.setLightOn(true);
					}

					LOGGER.debug("light sensor value is successfully applied.");
					Thread.sleep(500);

					// (3) reset the sensor value queues
					controller.resetSliderValues();
					controller.resetLightValues();
				} catch (InterruptedException e) {
					e.printStackTrace();
				}
			}
		}
	}

	private synchronized void addSliderValue(int value){
		this.sliderValues.add(value);
	}

	private int getLastSliderValue(){
		if(sliderValues.size()==0){
			return 0;
		}else {
			return this.sliderValues.get(sliderValues.size() - 1).intValue();
		}
	}

	private synchronized void resetSliderValues(){
		int lastVal = this.getLastSliderValue();
		this.sliderValues.clear();
		this.sliderValues.add(lastVal);
	}

	private synchronized void addLightValue(int value){
		this.lightValues.add(value);
	}

	private int getLastLightValue(){
		if(this.lightValues.size()==0){
			return 0;
		}else{
			return this.lightValues.get(lightValues.size()-1).intValue();
		}
	}

	private synchronized void resetLightValues(){
		int lastVal = this.getLastLightValue();
		this.lightValues.clear();
		this.lightValues.add(lastVal);
	}

	public StandLightAgent getAgent(){
		return this.agent;
	}
}

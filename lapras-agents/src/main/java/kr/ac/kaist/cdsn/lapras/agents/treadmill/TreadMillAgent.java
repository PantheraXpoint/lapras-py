package kr.ac.kaist.cdsn.lapras.agents.treadmill;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.phidgets.InterfaceKitPhidget;
import com.phidgets.PhidgetException;
import com.phidgets.event.AttachEvent;
import com.phidgets.event.AttachListener;
import com.phidgets.event.SensorChangeEvent;
import com.phidgets.event.SensorChangeListener;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.LaprasException;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.rest.RestServer;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;

/**
 * @author KyeongDeok Baek (WebEng Lab, blest215@kaist.ac.kr) 
 * @date 2017.08.21
 *
 */

public class TreadMillAgent extends AgentComponent {
	private static final Logger LOGGER = LoggerFactory.getLogger(TreadMillAgent.class);
	
	private InterfaceKitPhidget interfaceKit;
	private IRListener irListener;
	
	// 사용 중을 나타내는 Context
    @ContextField(publishAsUpdated = true)
    private Context isUsing;
    
    // IR Distance Sensor를 사용해 측정한 거리 값으로 사용 중을 판단
    // 디버깅 목적으로 만든 Context, Publish하지 않음
    @ContextField(publishAsUpdated = false)
    private Context distance;
	
	public TreadMillAgent(EventDispatcher eventDispatcher, Agent agent) {
		super(eventDispatcher, agent);

		isUsing.setInitialValue(false);
	}
	
	public static void main(String[] args){
        AgentConfig agentConfig = new AgentConfig("TreadMillAgent")
                .setBrokerAddress("tcp://smart-iot.kaist.ac.kr:18830")
                .setPlaceName("N1Lounge8F")
                .setOption("rest_port", "8083");

        Agent agent;
        try {
            agent = new Agent(TreadMillAgent.class, agentConfig);
            agent.addComponent(RestServer.class);
        } catch (LaprasException e) {
            LOGGER.error("Failed to initailize the agent", e);
            return;
        }

        agent.start();
    }

	@Override
	public void run() {
		try {
			// Phidget IR Distance Sensor 초기화
            interfaceKit = new InterfaceKitPhidget();
            irListener = new IRListener();
            interfaceKit.addSensorChangeListener(irListener);
            interfaceKit.addAttachListener(new attachListener());
            // interfaceKit.open(this.phidgetSerial);
            interfaceKit.openAny();
            interfaceKit.waitForAttachment();
        } catch (PhidgetException e) {
            LOGGER.error("Couldn't initialize Phidget interface kit", e);
            return;
        }
		
		while(true) {
        }
		
	}
    
	// IR Distance Sensor Listener
    public class IRListener implements SensorChangeListener {
    	// 사람이 앉아 있을 때 센서 값이 140 이상
    	// 사람이 없을 때 센서 값이 30~60 사이
    	int threshold = 100;

    	// TODO Serial 하드코딩된 상태, conf 파일에서 읽어오도록 변경 필요
    	private final int phidgetSerial = 454293;
    	private final int phidgetPort = 5;

    	// IR Sensor의 거리 측정값이 변할 때마다 수행
    	@Override
    	public void sensorChanged(SensorChangeEvent sensorEvent) {
    		if (sensorEvent.getIndex() != this.phidgetPort) return;
    		if (sensorEvent.getValue() > threshold) {
    			//if ((int) distance.getValue() < threshold) {isUsing.updateValue(true);}
    			isUsing.updateValue(true);
    		} else {
    			//if ((int) distance.getValue() > threshold) {isUsing.updateValue(false);}
    			isUsing.updateValue(false);
    		}
    		distance.updateValue(sensorEvent.getValue());
    	}

    }
    
    // Attach Listener
    private class attachListener implements AttachListener {
        @Override
        public void attached(AttachEvent ae) {
            LOGGER.info("Phidget Attached: {}", ae.toString());
        }
    }

}
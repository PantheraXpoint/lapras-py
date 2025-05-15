package kr.ac.kaist.cdsn.lapras.agents.whiteboard;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.*;

import com.phidgets.InterfaceKitPhidget;
import com.phidgets.PhidgetException;
import com.phidgets.event.SensorChangeEvent;
import com.phidgets.event.SensorChangeListener;


import kr.ac.kaist.cdsn.lapras.agents.door.DoorAgent;
import kr.ac.kaist.cdsn.lapras.rest.RestServer;


import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.LaprasException;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


import com.monnit.mine.MonnitMineAPI.Gateway;
import com.monnit.mine.MonnitMineAPI.MineServer;
import com.monnit.mine.MonnitMineAPI.Sensor;
import com.monnit.mine.MonnitMineAPI.SensorMessage;
import com.monnit.mine.MonnitMineAPI.iSensorMessageHandler;
import com.monnit.mine.MonnitMineAPI.enums.eGatewayType;
import com.monnit.mine.MonnitMineAPI.enums.eMineListenerProtocol;
import com.monnit.mine.MonnitMineAPI.enums.eSensorApplication;

import java.io.IOException;
import java.util.List;

import static jdk.nashorn.internal.parser.TokenKind.IR;

public class WhiteboardAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(WhiteboardAgent.class);

    @ContextField(publishAsUpdated = true)
    public boolean WhiteboardUsed;

    public boolean current;

    public WhiteboardAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);
    }

    /*public static void main(String... args) {


        AgentConfig agentConfig = new AgentConfig("WhiteboardAgent")
                .setBrokerAddress("tcp://smart-iot.kaist.ac.kr:18830")
                .setPlaceName("N1SeminarRoom825");


        try {
            Agent agent = new Agent(WhiteboardAgent.class, agentConfig);
            agent.addComponent(RestServer.class);
            agent.start();
        } catch (LaprasException e) {
            LOGGER.error("Could not instantiate the agent", e);
            return;
        }
    }*/

    @Override
    public void run() {

        InterfaceKitPhidget phidgetInterfaceKit;

        try {
            phidgetInterfaceKit = new InterfaceKitPhidget();


            /*
            IRDataListener irdListener = new IRDataListener();
            phidgetInterfaceKit.addSensorChangeListener(irdListener);
            */
            phidgetInterfaceKit.openAny();
            phidgetInterfaceKit.waitForAttachment();

            boolean current = false;
            contextManager.updateContext("WhiteboardUsed", false, agentName);
            System.out.println("Publish: not Used");

            double IR0_init = phidgetInterfaceKit.getSensorValue(0);
            double IR1_init = phidgetInterfaceKit.getSensorValue(1);
            double IR2_init = phidgetInterfaceKit.getSensorValue(2);


            IR0_init =  9462/(IR0_init - 16.92);
            IR1_init =  9462/(IR1_init - 16.92);
            IR2_init =  9462/(IR2_init - 16.92);

            System.out.println("!!!!!!!!!!!!!!!!!!!!!!\nIR0_init: " + IR0_init + "\nIR1_init: " + IR1_init + "\nIR2_init: " + IR2_init);

            int time = 0;

            while(true) {

                double IR0 = phidgetInterfaceKit.getSensorValue(0);
                double IR1 = phidgetInterfaceKit.getSensorValue(1);
                double IR2 = phidgetInterfaceKit.getSensorValue(2);

                if(IR0 > 80 && IR0 < 490)
                    IR0 =  9462/(IR0 - 16.92);
                else
                    IR0 = 0;

                if(IR1 > 80 && IR1 < 490)
                    IR1 =  9462/(IR1 - 16.92);
                else
                    IR1 = 0;

                if(IR2 > 80 && IR2 < 490)
                    IR2 =  9462/(IR2 - 16.92);
                else
                    IR2 = 0;

                System.out.println("IR0:" + IR0 + "\nIR1:" + IR1 + "\nIR2:" + IR2);

                if(IR0 > 30 && IR1 > 30 && IR2 > 30 ) {
                    if (Math.abs(IR0-IR0_init)>30 || Math.abs(IR1-IR1_init)>30 || Math.abs(IR1-IR1_init)>30) {
                        if (!current)
                            contextManager.updateContext("WhiteboardUsed", true, agentName);

                        if (Math.abs(IR0-IR0_init)>30 && IR0>30)
                            System.out.println("IR0 Used: " + IR0);
                        if (Math.abs(IR1-IR1_init)>30 && IR1>30)
                            System.out.println("IR1 Used: " + IR1);
                        if (Math.abs(IR2-IR2_init)>30 && IR2>30)
                            System.out.println("IR2 Used: " + IR2);
                        time = 0;
                        current = true;
                    }
                    else{
                        if(time <= 20)
                            time++;

                    }
                }
                else{

                    if(time <= 20)
                        time++;
                }


                if(time > 20)
                {
                    if(current){
                        contextManager.updateContext("WhiteboardUsed", false, agentName);
                        System.out.println("Publish: not Used");
                    }
                    current = false;

                }
                Thread.sleep(500);
            }

        } catch (PhidgetException e) {
            e.printStackTrace();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }


    }

    /*

    public class IRDataListener implements SensorChangeListener {

        @Override
        public void sensorChanged(SensorChangeEvent sensorEvent) {



            //20-150
            if(sensorEvent.getValue() > 80 && sensorEvent.getValue() < 490)
            {
                System.out.println("value : " + sensorEvent.getValue() + "\nDistance (cm) = " + 9462/(sensorEvent.getValue() - 16.92));

            }
            else
            {
                System.out.println("value is not valid!");
            }






        }


    }*/

}

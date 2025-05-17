package kr.ac.kaist.cdsn.lapras.agents.podium;

import com.phidgets.InterfaceKitPhidget;
import com.phidgets.PhidgetException;
import com.phidgets.event.*;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.Agent;

import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
//
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.rest.RestServer;
import kr.ac.kaist.cdsn.lapras.util.Resource;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;

import java.io.IOException;

/**
 * Created by Hyunju Kim on 2017-01-25.
 */
public class PodiumAgent extends AgentComponent {
    private static InterfaceKitPhidget phidget;
    public static final int SOUND_PHIDGET_IFK_SERIAL=-1;
    public static final int SOUND_SENSOR_INDEX = 0;


    public static int DISTANCE_SENSOR_INDEX_LEFT=2;
    public static int DISTANCE_SENSOR_INDEX_CENTER=3;
    public static int DISTANCE_SENSOR_INDEX_RIGHT=4;

    public static final int CONTEXT_REPORTING_PERIOD = 10000; // milliseconds



    @ContextField(publishAsUpdated = true)
    public Context present;

    @ContextField(publishAsUpdated = true)
    public Context soundC;

    @ContextField(publishAsUpdated = true)
    public Context Screen;
    public boolean Screen_state = false;

    public PodiumAgent(EventDispatcher eventDispatcher, Agent agent) {        super(eventDispatcher, agent);    }

    @Override
    public void run() {
        initPhidget(SOUND_PHIDGET_IFK_SERIAL);

        int Screen_init = 0;

        while(true){
            try{

                soundC.updateValue((Math.log(phidget.getSensorValue(SOUND_SENSOR_INDEX))*16.801+9.872));
                present.updateValue((phidget.getSensorValue(DISTANCE_SENSOR_INDEX_LEFT)+phidget.getSensorValue(DISTANCE_SENSOR_INDEX_CENTER)+phidget.getSensorValue(DISTANCE_SENSOR_INDEX_RIGHT))/3);

            }
            catch (PhidgetException e) {
                e.printStackTrace();
            }
            try {
                Thread.sleep(CONTEXT_REPORTING_PERIOD);
            } catch (InterruptedException e) {
                break;
            }
        }

    }
    private static void initPhidget(int serialNo){
        try {
            //

            // Open PhidgetInterfaceKit
            phidget = new InterfaceKitPhidget();

            // opens interface kit using the serial number.
            // if the serial number is invalid, just open anything attached.
            if (serialNo > 0)
                phidget.open(serialNo);
            else
                phidget.openAny();

            System.out.println(" [PhidgetSensor] waiting for InterfaceKit attachment...");
            phidget.waitForAttachment(2000);
            System.out.println("   -attached: " + phidget.getDeviceID() + " (s/n: " + phidget.getSerialNumber() + ")");

            /**
             * After creating a Phidget object called "phidget" and before
             * opening the object
             *
             * @author Lotfi
             *
             */
            phidget.addAttachListener(new AttachListener() {
                public void attached(AttachEvent ae) {
                    System.out.println("attachment of " + ae);
                }
            });
            phidget.addDetachListener(new DetachListener() {
                public void detached(DetachEvent ae) {
                    System.out.println("detachment of " + ae);
                }
            });
            phidget.addErrorListener(new ErrorListener() {
                public void error(ErrorEvent ee) {
                    System.out.println("error event for " + ee);
                }
            });
            phidget.addInputChangeListener(new InputChangeListener() {
                public void inputChanged(InputChangeEvent oe) {
                    System.out.println(oe);
                }
            });
            phidget.addOutputChangeListener(new OutputChangeListener() {
                // called when output state changes
                public void outputChanged(OutputChangeEvent e) {
                    // Redirect
                    System.out.println(e);
                }
            });
        } catch (PhidgetException e) {
            System.err.println(
                    "  [PhidgetSensor] ERROR opening interface kit! Please check the serial number. (input serialNo = "
                            + serialNo + ")");
            e.printStackTrace();
        }
    }
}

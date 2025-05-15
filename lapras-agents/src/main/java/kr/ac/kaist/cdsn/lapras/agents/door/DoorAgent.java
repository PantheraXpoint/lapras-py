package kr.ac.kaist.cdsn.lapras.agents.door;

import com.phidgets.InterfaceKitPhidget;
import com.phidgets.PhidgetException;
import com.phidgets.event.SensorChangeEvent;
import com.phidgets.event.SensorChangeListener;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityMethod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Created by Daekeun Lee on 2016-11-24.
 */
public class DoorAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(DoorAgent.class);

    private static final long IR_TIMER_RESET_TASK_PERIOD = 3000L;

    private InterfaceKitPhidget interfaceKit;
    private IRDataListener irdListener;

    @ContextField(publishAsUpdated = true)
    private Context userCount;

    @ContextField(publishAsUpdated = true)
    private Context correctedUserCount;

    public DoorAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        correctedUserCount.setInitialValue(0);
        userCount.setInitialValue(0);
    }

    @Override
    public void run() {
        try {
            interfaceKit = new InterfaceKitPhidget();
            irdListener = new IRDataListener();
            interfaceKit.addSensorChangeListener(irdListener);
            interfaceKit.openAny();
            interfaceKit.waitForAttachment();
        } catch (PhidgetException e) {
            LOGGER.error("Couldn't initialize Phidget interface kit", e);
            return;
        }

        while(true) {
            try {
                Thread.sleep(IR_TIMER_RESET_TASK_PERIOD);
                irdListener.timeout();
            } catch (InterruptedException e) {
                break;
            }
        }
    }

    @FunctionalityMethod
    public void increaseUserCount() {
        userCount.updateValue((Integer)userCount.getValue() + 1);
    }

    @FunctionalityMethod
    public void decreaseUserCount() {
        userCount.updateValue(Math.max(0, (Integer)userCount.getValue() - 1));
    }

    /**
     * IR sensor의 데이터가 변경될 때마다 수행되어야 하는 로직이 구현된 클래스.
     *
     * @author Sanggyu Nam (WebEng Lab, sanggyu.nam@kaist.ac.kr)
     * @date 2016.05.11
     */
    public class IRDataListener implements SensorChangeListener {
        int[] frontSensor = { 0, 0 };   // 앞쪽에 있는 센서.
        int[] backSensor = { 0, 0 };    // 뒤쪽에 있는 센서.
        int[] send = { 0, 0, 0, 0 };    // 센서값을 보내기 위한 배열?
        int threshold = 200;            // noise를 줄이기 위한 threshold.
        long passNum = 0;               // 사용자가 통과하는 이벤트의 발생 횟수. 통과가 감지될 때마다 방향에 관계없이 값이 1 증가합니다.
        public int flag = 0;            // 앞쪽과 뒷쪽 두 센서가 감지한 값이 threshold를 넘은 횟수.
        private boolean userPassed = false;     // 현재 두 센서를 활성화한 사용자가 문을 통과했는지를 나타냅니다.

        /**
         * IR sensor가 감지한 값의 변화를 토대로 listener의 상태를 변화시키고,
         * 필요한 경우 문을 지나간 사람의 횟수를 계산하여 이를 publish합니다.
         *
         * {@link #flag}의 값이 짝수일 경우, pass count를 publish합니다.  이는
         * 다음과 근거를 둔 휴리스틱입니다.
         *
         * 만약 사람이 세미나룸 안으로 들어갈 때, 이상적인 경우 앞쪽 센서와
         * 뒷쪽 센서에서 한 번씩 센싱할 것입니다. 그래서 짝수입니다.
         *
         * 문제는 세 번 또는 다섯 번 정도 센싱이 발생할 수 있는데, 이 때 사람이
         * 밖으로 나갔는지, 안으로 들어왔는지 정확하게 알기가 어렵습니다.
         *
         * @param sensorEvent sensor에 발생한 이벤트
         */
        @Override
        public void sensorChanged(SensorChangeEvent sensorEvent) {
            /*
             * IR센서가 listening 방식이라 다른 쓰레드가 이미 연산을 처리할 경우,
             * 아래 루틴으로 진입하지 못하게 막을 방법이 필요합니다.
             */
            synchronized (this) {
                boolean frontSensorChanged = (0 == sensorEvent.getIndex());
                if (sensorEvent.getValue() > threshold) {
                    boolean sensorActivatedBefore = frontSensorChanged ? (frontSensor[0] == 1) : (backSensor[0] == 1);
                    if (!sensorActivatedBefore) {
                        ++flag;
                        userPassed = false;
                        if (frontSensorChanged) {
                            DoorAgent.LOGGER.info("Sensor 1 is on");
                            frontSensor[0] = 1;         // send = 1xxx
                            if (backSensor[0] == 1) {
                                frontSensor[1] = 1;     // send = 111x
                            } else {
                                frontSensor[1] = 0;     // send = 100x
                            }
                        } else {
                            DoorAgent.LOGGER.info("Sensor 2 is on");
                            backSensor[0] = 1;          // send = xx1x
                            if (frontSensor[0] == 1) {
                                backSensor[1] = 1;      // send = 1x11
                            } else {
                                backSensor[1] = 0;      // send = 0x10
                            }
                        }
                    }
                    send[0] = frontSensor[0];
                    send[1] = frontSensor[1];
                    send[2] = backSensor[0];
                    send[3] = backSensor[1];

                    DoorAgent.LOGGER.info("flag: {}", flag);

                } else {                                    // value < threshold
                    if (frontSensorChanged) {
                        frontSensor[0] = 0;
                        frontSensor[1] = 0;
                    } else {
                        backSensor[0] = 0;
                        backSensor[1] = 0;
                    }
                }

                // 두 센서가 차례로 임계치를 넘는 값을 반환하지 않았다면 센서 리스너의 작업을 여기서 멈춥니다.
                boolean sensorActivatedInOrder = ((send[0] == 1) && (send[2] == 1));
                if (!sensorActivatedInOrder) {
                    return;
                }

                // 사용자가 문을 통과하면, 사용자의 진행 방향을 나타내는 컨텍스트 메시지를 발행합니다.
                final boolean gettingOut = ((send[1] == 1) && (send[3] != 1));                  // send = 1110
                final boolean gettingIn = (!gettingOut && (send[3] == 1) && (send[1] != 1));    // send = 1011
                final boolean somebodyNearDoor = (gettingOut || gettingIn);
                final boolean justPassed = somebodyNearDoor && !userPassed && 0 == flag % 2;
                if (justPassed) {
                    userPassed = true;
                    ++passNum;
                }
                final boolean shouldPublish = somebodyNearDoor && justPassed;

                if (shouldPublish) {
                    String actionName = gettingIn ? "Entrance" : "Exit";
                    int diff = gettingIn ? 1 : -1;
                    actionManager.taken(actionName);
                    Integer currentValue = (Integer) userCount.getValue();
                    Integer currentValue2 = (Integer) correctedUserCount.getValue();
                    userCount.updateValue(currentValue + diff >= 0 ? currentValue + diff : 0);
                    correctedUserCount.updateValue(currentValue2 + diff >= 0 ? currentValue + diff : 0);
                }

                // 사용자 진행 방향을 파악하기 위해 기록한 데이터를 초기화합니다.
                flag = 0;
                for (int i = 0; i < 4; ++i) {
                    send[i] = 0;
                }
            }
        }

        public void timeout() {
            synchronized (this) {
                for (int i = 0; i < 4; ++i) {
                    send[i] = 0;
                }

                frontSensor[0] = 0;
                frontSensor[1] = 0;
                backSensor[0] = 0;
                backSensor[1] = 0;
                flag = 0;
                DoorAgent.LOGGER.debug("reset the sensing data for the user's direction");
            }
        }
    }
}

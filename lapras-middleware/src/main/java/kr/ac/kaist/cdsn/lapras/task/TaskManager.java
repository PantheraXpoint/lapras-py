package kr.ac.kaist.cdsn.lapras.task;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.communicator.LaprasTopic;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

/**
 * Created by Daekeun Lee on 2017-02-15.
 */
public class TaskManager extends Component {
    private static final Logger LOGGER = LoggerFactory.getLogger(TaskManager.class);

    private Map<Integer, TaskInstance> ongoingTasks = new HashMap<>();

    public TaskManager(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);
    }

    public Collection<TaskInstance> listTasks() {
        return ongoingTasks.values();
    }

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.MESSAGE_ARRIVED);
        subscribeEvent(EventType.TASK_INITIATED);
        subscribeEvent(EventType.TASK_TERMINATED);
    }

    @Override
    public void setUp() {
        //LaprasTopic topic = new LaprasTopic(null, MessageType.TASK, LaprasTopic.SINGLELEVEL_WILDCARD);
        LaprasTopic topic = new LaprasTopic(null, MessageType.TASK_INITIATION, LaprasTopic.SINGLELEVEL_WILDCARD);
        agent.getMqttCommunicator().subscribeTopic(topic);
        topic = new LaprasTopic(null, MessageType.TASK_TERMINATION, LaprasTopic.SINGLELEVEL_WILDCARD);
        agent.getMqttCommunicator().subscribeTopic(topic);
    }

    @Override
    protected boolean handleEvent(Event event) {
        switch(event.getType()) {
            case MESSAGE_ARRIVED:
                LaprasTopic topic = (LaprasTopic) ((Object[]) event.getData())[0];

                if(topic.getMessageType() == MessageType.TASK_INITIATION) {
                    byte[] payload = (byte[]) ((Object[]) event.getData())[1];
                    TaskInitiation taskInitiation = TaskInitiation.fromPayload(payload);
                    if (taskInitiation != null) {
                        TaskInstance taskInstance = new TaskInstance(taskInitiation.getId(),
                                taskInitiation.getName(),
                                taskInitiation.getInvolvedUsers());
                        ongoingTasks.put(taskInstance.getId(), taskInstance);
                        dispatchEvent(EventType.TASK_INITIATED, taskInstance);
                        LOGGER.debug("Task initiated; id: {}, name: {}", taskInitiation.getId(), taskInitiation.getName());
                    }
                } else if (topic.getMessageType() == MessageType.TASK_TERMINATION) {
                    LOGGER.debug("Task termination message arrived");
                    byte[] payload = (byte[]) ((Object[]) event.getData())[1];
                    TaskTermination taskTermination = TaskTermination.fromPayload(payload);
                    if (taskTermination != null) {
                        LOGGER.debug("Task id: {}", taskTermination.getTaskId());
                        TaskInstance taskInstance = ongoingTasks.get(taskTermination.getTaskId());
                        LOGGER.debug("Task: {}", taskInstance);
                        if(taskInstance != null) {
                            ongoingTasks.remove(taskTermination.getTaskId());
                            dispatchEvent(EventType.TASK_TERMINATED, taskInstance);
                        }
                    }
                } else return true;
                break;
            case TASK_INITIATED:
                TaskInstance task = (TaskInstance) event.getData();
                LOGGER.debug("Task notified: {}", task.getTaskName());
                break;
            case TASK_TERMINATED:
                task = (TaskInstance) event.getData();
                LOGGER.debug("Task terminated: {}", task.getTaskName());
                break;
        }
        return true;
    }
}

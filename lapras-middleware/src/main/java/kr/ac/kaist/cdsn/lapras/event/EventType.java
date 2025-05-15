package kr.ac.kaist.cdsn.lapras.event;

/**
 * Created by Daekeun Lee on 2016-11-11.
 */
public enum EventType {
    SUBSCRIBE_TOPIC_REQUESTED,
    PUBLISH_MESSAGE_REQUESTED,
    MESSAGE_ARRIVED,
    CONTEXT_UPDATED,
    ACTION_TAKEN,
    TASK_NOTIFIED, /*Deprecated?*/
    TASK_INITIATED,
    TASK_TERMINATED,
    USER_NOTIFIED
}

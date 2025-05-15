package kr.ac.kaist.cdsn.lapras.event;

import kr.ac.kaist.cdsn.lapras.Component;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArraySet;

/**
 * Created by Daekeun Lee on 2016-11-11.
 */
public class EventDispatcher implements Runnable {
    private Thread thread;
    private EventQueue eventQueue;
    private Map<EventType, Set<EventConsumer>> consumerMap;

    public EventDispatcher() {
        this.eventQueue = new EventQueue();
        this.consumerMap = new ConcurrentHashMap<>();
    }

    public void start() {
        this.thread = new Thread(this);
        this.thread.setName(EventDispatcher.class.getSimpleName());
        this.thread.setDaemon(true);

        this.thread.start();
    }

    public void addSubscription(EventType eventType, Component component) {
        Set<EventConsumer> consumers = this.consumerMap.getOrDefault(eventType, new CopyOnWriteArraySet<>());
        consumers.add(component);
        this.consumerMap.put(eventType, consumers);
    }

    public void dispatch(Event event) throws InterruptedException {
        this.eventQueue.put(event);
    }

    public void run() {
        while(true) {
            Event event;
            try {
                event = eventQueue.take();
            } catch (InterruptedException e) {
                return;
            }
            Set<EventConsumer> consumers = this.consumerMap.get(event.getType());
            if(consumers == null) continue;
            for(EventConsumer consumer : consumers) {
                consumer.receiveEvent(event);
            }
        }
    }
}

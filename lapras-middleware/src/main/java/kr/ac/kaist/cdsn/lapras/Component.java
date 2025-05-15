package kr.ac.kaist.cdsn.lapras;

import kr.ac.kaist.cdsn.lapras.event.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Created by Daekeun Lee on 2016-11-11.
 */
public abstract class Component implements EventConsumer {
    private static final Logger LOGGER = LoggerFactory.getLogger(Component.class);

    private Thread thread;
    private final EventDispatcher eventDispatcher;
    protected final EventQueue eventQueue;
    protected final Agent agent;

    public Component(EventDispatcher eventDispatcher, Agent agent) {
        this.eventDispatcher = eventDispatcher;
        this.agent = agent;
        this.eventQueue = new EventQueue();
        subscribeEvents();
    }

    public void start() {
        this.thread = new Thread(() -> eventHandlingLoop());
        this.thread.setName(String.format("%s Event Handler", this.getClass().getSimpleName()));
        this.thread.setDaemon(true);
        this.thread.start();
    }

    public void terminate() {
        this.thread.interrupt();
        try {
            this.thread.join();
        } catch (InterruptedException e) {
        }
    }

    public void setUp() {
    }

    protected abstract void subscribeEvents();

    protected abstract boolean handleEvent(Event event);

    private void eventHandlingLoop() {
        setUp();
        while(true) {
            try {
                Event event = this.eventQueue.take();
                if(!handleEvent(event)) {
                    this.eventQueue.put(event);
                }
            } catch (InterruptedException e) {
                break;
            } catch (Exception e) {
                LOGGER.error("An error occurred while handling an event", e);
            }
        }
    }

    @Override
    public void receiveEvent(Event e) {
        eventQueue.add(e);
    }

    protected void dispatchEvent(final EventType eventType, final Object eventData) {
        dispatchEvent(new Event() {
            @Override
            public EventType getType() {
                return eventType;
            }

            @Override
            public Object getData() {
                return eventData;
            }
        });
    }

    protected void dispatchEvent(Event event) {
        try {
            this.eventDispatcher.dispatch(event);
        } catch (InterruptedException e) {
        }
    }

    protected void subscribeEvent(EventType eventType) {
        eventDispatcher.addSubscription(eventType, this);
    }
}

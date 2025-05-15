package kr.ac.kaist.cdsn.lapras.agents.shade;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.functionality.FunctionalityMethod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;

/**
 * Created by JWP on 2017. 8. 7.
 * ShadeAgent controls the electronic shade remotely.
 */
public class ShadeAgent extends AgentComponent{
    private static final Logger LOGGER = LoggerFactory.getLogger(ShadeAgent.class);

    private static String[] channelList = {"Left", "Center", "Right", "None", "All"};

    private final ShadeSwitch rollUpSwitch;
    private final ShadeSwitch rollDownSwitch;
    private final ShadeSwitch stopSwitch;
    private final ShadeSwitch channelSwitch;
    private ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
    private ScheduledFuture<?> future;


    private Integer currentChannelIdx;
    private Integer switchChannelFlag;

    @ContextField(publishAsUpdated = true)
    public Context channel;

    public ShadeAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        AgentConfig agentConfig = agent.getAgentConfig();
        rollUpSwitch = new ShadeSwitch(agentConfig.getOption("gpio_rollup"));
        rollDownSwitch = new ShadeSwitch(agentConfig.getOption("gpio_rolldown"));
        stopSwitch = new ShadeSwitch(agentConfig.getOption("gpio_stop"));
        channelSwitch = new ShadeSwitch(agentConfig.getOption("gpio_channel"));

        currentChannelIdx = 0; // To-do: how to track initial channel?
        switchChannelFlag = 0;
        channel.updateValue(channelList[currentChannelIdx]);
    }

    @Override
    public void run() {
        try {
            while (true) {
                Thread.sleep((Integer.MAX_VALUE));
            }
        } catch (InterruptedException e) { }
    }

    @FunctionalityMethod
    public void rollUpShade() throws InterruptedException {
        rollUpSwitch.switchOn();

        LOGGER.info("Roll up shade");
    }

    @FunctionalityMethod
    public void rollDownShade() throws InterruptedException {
        rollDownSwitch.switchOn();
        LOGGER.info("Roll up shade");
    }

    @FunctionalityMethod
    public void stopShade() throws InterruptedException {
        stopSwitch.switchOn();
        LOGGER.info("Roll up shade");
    }

    /**
     *
     * @throws InterruptedException
     *
     * switchOn() does not change the channel when executed at first(?).
     * Subsequent switchOn() call within 5 second is needed to switch channel.
     *
     * -- Example execution (1)--
     * 1. Call switchOn() -> ready for changing channel
     * 2. Call switchOn() within 5 seconds -> switch channel
     *
     * -- Example execution (2)--
     * 1. Call switchOn() -> ready for changing channel
     * 2. Call switchOn() after 5 seconds -> ready for changing channel
     */

    @FunctionalityMethod()
    public void switchChannel() throws InterruptedException {

        LOGGER.info("Switch channel");

        if (switchChannelFlag == 0) {
            channelSwitch.switchOn();
            Thread.sleep(500);
            channelSwitch.switchOn();
            switchChannelFlag = 1;

            updateChannel();

        } else {
            future.cancel(true);
            channelSwitch.switchOn();

            updateChannel();
        }

        future = scheduler.schedule(()->{
            switchChannelFlag = 0;
        }, 5, TimeUnit.SECONDS);
    }

    private void updateChannel() {
        currentChannelIdx += 1;

        if (currentChannelIdx == channelList.length) {
            currentChannelIdx = 0;
        }

        channel.updateValue(channelList[currentChannelIdx]);

    }

}
